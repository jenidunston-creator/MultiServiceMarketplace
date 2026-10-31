import csv

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import security
from .decorators import role_required
from .forms import ROLE_MAP, ProviderProfileForm, SignupForm
from bookings.models import Booking, Complaint, Payment, Payout, Quotation, Review
from communication.models import ChatConversation
from services.models import ServiceProviderService, ServiceRequest
from .models import Business, IdentityVerification, ProviderProfile, User


def signup_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = SignupForm(request.POST)
        if security.too_many(f'signup:{security.client_ip(request)}', 8, 3600):
            messages.error(request, 'Too many sign-ups from this computer. Please try again later.')
            return render(request, 'accounts/signup.html', {'form': form})
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Welcome to Servana! Please verify your account to start using it.')
            return redirect('verify_center')
    else:
        # the footer links use ?role=provider etc. to pre-select the account type
        role = request.GET.get('role')
        form = SignupForm(initial={'role': role} if role in ROLE_MAP else {})

    return render(request, 'accounts/signup.html', {'form': form})


@login_required
def dashboard_redirect(request):
    """Send each user to the dashboard that matches their role."""
    user = request.user

    if user.is_superuser or user.role == User.Role.ADMIN:
        return redirect('admin_dashboard')
    if user.role == User.Role.SERVICE_PROVIDER:
        return redirect('provider_dashboard')
    if user.role == User.Role.BUSINESS:
        return redirect('business_dashboard')
    return redirect('customer_dashboard')


@role_required(User.Role.CUSTOMER)
def customer_dashboard(request):
    bookings = Booking.objects.filter(customer__user=request.user).select_related('service')
    active = [Booking.Status.PENDING, Booking.Status.CONFIRMED, Booking.Status.IN_PROGRESS]
    return render(request, 'dashboards/customer.html', {
        'active_count': bookings.filter(status__in=active).count(),
        'completed_count': bookings.filter(status=Booking.Status.COMPLETED).count(),
        'quotes_waiting': Quotation.objects.filter(
            service_request__customer__user=request.user,
            status=Quotation.Status.PENDING).count(),
        'reviews_count': Review.objects.filter(customer__user=request.user).count(),
        'recent': bookings.order_by('-created_at')[:5],
    })


@role_required(User.Role.SERVICE_PROVIDER)
def provider_dashboard(request):
    listings = ServiceProviderService.objects.filter(
        provider__user=request.user
    ).select_related('service', 'service__category').order_by('-created_at')
    jobs = Booking.objects.filter(provider__user=request.user).select_related(
        'service', 'customer__user').order_by('-created_at')
    average = Review.objects.filter(
        provider__user=request.user, is_approved=True).aggregate(a=Avg('rating'))['a']
    my_payments = Payment.objects.filter(booking__provider__user=request.user)
    my_payouts = Payout.objects.filter(provider__user=request.user).select_related('payment__booking__service')
    paid_out = my_payouts.aggregate(t=Sum('amount'))['t']
    held = my_payments.filter(status__in=[Payment.Status.PART_HELD, Payment.Status.HELD]).aggregate(
        t=Sum('amount_paid'))['t']
    return render(request, 'dashboards/provider.html', {
        'money_received': paid_out or 0,
        'payouts': my_payouts[:10],
        'money_held': held or 0,
        'profile': ProviderProfile.objects.filter(user=request.user).first(),
        'listings': listings,
        'live_count': listings.filter(is_active=True).count(),
        'jobs': jobs[:5],
        'pending_count': jobs.filter(status=Booking.Status.PENDING).count(),
        'request_count': ServiceRequest.objects.filter(
            provider_matches__provider__user=request.user,
            status=ServiceRequest.Status.OPEN,
        ).exclude(quotations__provider__user=request.user).count(),
        'avg_rating': round(average, 1) if average else None,
    })


@role_required(User.Role.SERVICE_PROVIDER)
def provider_profile_edit(request):
    profile, _ = ProviderProfile.objects.get_or_create(
        user=request.user, defaults={'provider_name': request.user.get_full_name() or request.user.username})

    if request.method == 'POST':
        form = ProviderProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been saved.')
            return redirect('provider_dashboard')
    else:
        form = ProviderProfileForm(instance=profile)

    return render(request, 'accounts/provider_profile.html', {'form': form})


def get_business(user):
    """The business that belongs to this user (made if it is missing)."""
    business = user.businesses.first()
    if business is None:
        business = Business.objects.create(
            owner=user, business_name=f"{user.get_full_name() or user.username} Business")
    return business


@role_required(User.Role.BUSINESS)
def business_dashboard(request):
    business = get_business(request.user)
    bookings = Booking.objects.filter(customer__user=request.user).select_related('service', 'provider')
    this_month = bookings.filter(created_at__year=timezone.now().year,
                                 created_at__month=timezone.now().month)
    open_statuses = [Booking.Status.PENDING, Booking.Status.CONFIRMED, Booking.Status.IN_PROGRESS]
    spent = this_month.exclude(status=Booking.Status.CANCELLED).aggregate(t=Sum('agreed_price'))['t']
    return render(request, 'dashboards/business.html', {
        'business': business,
        'total_count': bookings.count(),
        'open_count': bookings.filter(status__in=open_statuses).count(),
        'month_count': this_month.count(),
        'month_spent': spent or 0,
        'recent': bookings.order_by('-created_at')[:8],
    })


# ---------------------------------------------------------------- admin
@role_required(User.Role.ADMIN)
def admin_dashboard(request):
    status_counts = {row['status']: row['n'] for row in
                     Booking.objects.values('status').annotate(n=Count('id'))}
    total_bookings = sum(status_counts.values())
    status_bars = [{
        'label': label, 'count': status_counts.get(value, 0),
        'percent': round(status_counts.get(value, 0) * 100 / total_bookings) if total_bookings else 0,
    } for value, label in Booking.Status.choices]

    top_services = Booking.objects.values('service__name').annotate(n=Count('id')).order_by('-n')[:5]
    top_max = top_services[0]['n'] if top_services else 1
    revenue = Payment.objects.filter(status__in=[Payment.Status.PART_HELD, Payment.Status.HELD, Payment.Status.RELEASED]
                                     ).aggregate(t=Sum('amount_paid'))['t']

    return render(request, 'dashboards/admin.html', {
        'user_count': User.objects.count(),
        'provider_count': ProviderProfile.objects.count(),
        'booking_count': total_bookings,
        'revenue': revenue or 0,
        'ids_waiting': IdentityVerification.objects.filter(status=IdentityVerification.Status.PENDING).count(),
        'payments_waiting': Payment.objects.filter(status=Payment.Status.HELD,
                                                   customer_confirmed_at__isnull=False).count(),
        'complaints_open': Complaint.objects.filter(
            status__in=[Complaint.Status.OPEN, Complaint.Status.IN_REVIEW]).count(),
        'open_chats': ChatConversation.objects.filter(escalated=True, is_active=True).count(),
        'status_bars': status_bars,
        'top_services': [{'name': r['service__name'], 'count': r['n'],
                          'percent': round(r['n'] * 100 / top_max)} for r in top_services],
        'users': User.objects.order_by('-date_joined')[:15],
        'pending_providers': ProviderProfile.objects.filter(
            verification_status=ProviderProfile.VerificationStatus.PENDING).select_related('user'),
        'reviews': Review.objects.select_related(
            'customer__user', 'provider', 'booking__service').order_by('-created_at')[:10],
        'chats': ChatConversation.objects.filter(
            escalated=True, is_active=True).select_related('user')[:10],
    })


@role_required(User.Role.ADMIN)
@require_POST
def admin_user_toggle(request, pk):
    person = get_object_or_404(User, pk=pk)
    if person == request.user or person.is_superuser:
        messages.error(request, 'You cannot deactivate yourself or a superuser.')
    else:
        person.is_active = not person.is_active
        person.save()
        messages.success(request, f"{person.username} is now {'active' if person.is_active else 'deactivated'}.")
    return redirect('admin_dashboard')


@role_required(User.Role.ADMIN)
@require_POST
def admin_provider_verify(request, pk):
    provider = get_object_or_404(ProviderProfile, pk=pk)
    choice = request.POST.get('decision')
    if choice == 'verify':
        provider.verification_status = ProviderProfile.VerificationStatus.VERIFIED
    elif choice == 'reject':
        provider.verification_status = ProviderProfile.VerificationStatus.REJECTED
    else:
        return redirect('admin_dashboard')
    provider.save()
    messages.success(request, f'{provider.provider_name}: {provider.get_verification_status_display()}.')
    return redirect('admin_dashboard')


@role_required(User.Role.ADMIN)
@require_POST
def admin_review_toggle(request, pk):
    review = get_object_or_404(Review, pk=pk)
    review.is_approved = not review.is_approved
    review.save()
    messages.success(request, 'Review approved.' if review.is_approved else 'Review hidden.')
    return redirect('admin_dashboard')


@role_required(User.Role.ADMIN)
def admin_bookings_csv(request):
    """Download all bookings as a spreadsheet file."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="bookings.csv"'
    writer = csv.writer(response)
    writer.writerow(['ID', 'Service', 'Customer', 'Provider', 'Date', 'Price', 'Status', 'Payment'])
    for b in Booking.objects.select_related('service', 'customer__user', 'provider', 'payment'):
        payment = b.payment.get_status_display() if hasattr(b, 'payment') else 'Not paid'
        writer.writerow([b.pk, b.service.name, b.customer.user.username, b.provider.provider_name,
                         b.booking_date, b.agreed_price, b.get_status_display(), payment])
    return response
