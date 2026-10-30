from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify

from accounts.decorators import role_required
from accounts.models import User
from .forms import ServiceListingForm
from .models import ServiceCategory, ServiceProviderService
from bookings.models import Review


# Only providers who are fully verified (email, mobile, passport and visa) are shown to customers.
VERIFIED_PROVIDER = (
    Q(provider__user__is_superuser=True) | Q(provider__user__role=User.Role.ADMIN)
    | Q(provider__user__email_verified=True, provider__user__phone_verified=True,
        provider__user__id_verified=True)
)


def with_ratings(queryset):
    """Add avg_rating and review_count to each listing."""
    approved = Q(provider__received_reviews__is_approved=True)
    return queryset.annotate(
        avg_rating=Avg('provider__received_reviews__rating', filter=approved),
        review_count=Count('provider__received_reviews', filter=approved, distinct=True),
    )


def can_manage(user, listing):
    """Admins can manage any listing. A provider can manage only their own."""
    if user.is_superuser or user.role == User.Role.ADMIN:
        return True
    return listing.provider.user_id == user.id


# ---------- HOME PAGE (shows the latest real reviews) ----------
def home(request):
    reviews = (Review.objects.filter(is_approved=True)
               .exclude(comment='')
               .select_related('customer__user', 'provider', 'booking__service')
               .order_by('-created_at')[:3])
    return render(request, 'home.html', {'home_reviews': reviews})


# ---------- READ (list + search + filter) ----------
def service_list(request):
    listings = ServiceProviderService.objects.filter(is_active=True).filter(VERIFIED_PROVIDER).select_related(
        'provider', 'service', 'service__category'
    )

    q = request.GET.get('q', '').strip()
    category = request.GET.get('category', '')
    city = request.GET.get('location', '')

    if q:
        listings = listings.filter(
            Q(service__name__icontains=q)
            | Q(description__icontains=q)
            | Q(provider__provider_name__icontains=q)
        )
    if category and not category.isdigit():
        # the home page cards use words such as "home-maintenance" or "delivery"
        wanted = slugify(category)
        for c in ServiceCategory.objects.filter(is_active=True):
            if wanted in slugify(c.name):
                category = str(c.id)
                break
        else:
            category = ''
    if category:
        listings = listings.filter(service__category_id=category)
    if city:
        listings = listings.filter(provider__city__iexact=city)

    listings = with_ratings(listings).order_by('-created_at')

    # show 12 services per page
    page = Paginator(listings, 12).get_page(request.GET.get('page'))
    params = request.GET.copy()
    params.pop('page', None)

    return render(request, 'services/service_list.html', {
        'listings': page,
        'page': page,
        'query_string': params.urlencode(),
        'categories': ServiceCategory.objects.filter(is_active=True),
        'selected_category': category,
        'selected_city': city,
        'q': q,
        'cities': ['Auckland', 'Wellington', 'Christchurch', 'Hamilton',
                   'Tauranga', 'Dunedin', 'Queenstown', 'Rotorua', 'Nelson'],
    })


# ---------- READ (one service) ----------
def service_detail(request, pk):
    listing = get_object_or_404(
        with_ratings(ServiceProviderService.objects.select_related(
            'provider', 'service', 'service__category')),
        pk=pk,
    )
    # hidden listings, and listings of unverified providers, can only be seen by the owner or an admin
    owner = listing.provider.user
    provider_verified = owner.is_verified
    if not listing.is_active or not provider_verified:
        if not request.user.is_authenticated or not can_manage(request.user, listing):
            raise PermissionDenied

    reviews = listing.provider.received_reviews.filter(is_approved=True).select_related('customer__user')
    can_edit = request.user.is_authenticated and can_manage(request.user, listing)

    # Only customers and businesses can book or ask for a quote (visitors are sent to log in).
    if request.user.is_authenticated:
        can_book = request.user.role in (User.Role.CUSTOMER, User.Role.BUSINESS) \
            and not request.user.is_superuser and listing.provider.user_id != request.user.id
    else:
        can_book = True

    return render(request, 'services/service_detail.html', {
        'listing': listing,
        'reviews': reviews,
        'can_edit': can_edit,
        'can_book': can_book,
    })


# ---------- COMPARE ----------
def service_compare(request):
    ids = request.GET.getlist('compare')[:3]          # at most 3 columns
    listings = []
    if ids:
        listings = with_ratings(
            ServiceProviderService.objects.filter(pk__in=ids, is_active=True).filter(VERIFIED_PROVIDER)
            .select_related('provider', 'service')
        )
    return render(request, 'services/compare.html', {'listings': listings})


# ---------- CREATE ----------
@role_required(User.Role.SERVICE_PROVIDER)
def service_create(request):
    provider = request.user.provider_profile          # set up when the provider signed up

    if request.method == 'POST':
        form = ServiceListingForm(request.POST, request.FILES, provider=provider)
        if form.is_valid():
            listing = form.save(commit=False)
            listing.provider = provider               # the logged-in provider owns it
            listing.save()
            messages.success(request, 'Your service has been added.')
            return redirect('provider_dashboard')
    else:
        form = ServiceListingForm(provider=provider)

    return render(request, 'services/service_form.html', {'form': form, 'editing': False})


# ---------- UPDATE ----------
@role_required(User.Role.SERVICE_PROVIDER, User.Role.ADMIN)
def service_update(request, pk):
    listing = get_object_or_404(ServiceProviderService, pk=pk)
    if not can_manage(request.user, listing):
        raise PermissionDenied

    if request.method == 'POST':
        form = ServiceListingForm(request.POST, request.FILES, instance=listing,
                                  provider=listing.provider)
        if form.is_valid():
            form.save()
            messages.success(request, 'Service updated.')
            return redirect('service_detail', pk=listing.pk)
    else:
        form = ServiceListingForm(instance=listing, provider=listing.provider)

    return render(request, 'services/service_form.html', {
        'form': form, 'editing': True, 'listing': listing})


# ---------- DELETE ----------
@role_required(User.Role.SERVICE_PROVIDER, User.Role.ADMIN)
def service_delete(request, pk):
    listing = get_object_or_404(ServiceProviderService, pk=pk)
    if not can_manage(request.user, listing):
        raise PermissionDenied

    if request.method == 'POST':
        listing.delete()
        messages.success(request, 'Service deleted.')
        return redirect('dashboard')

    return render(request, 'services/service_confirm_delete.html', {'listing': listing})
