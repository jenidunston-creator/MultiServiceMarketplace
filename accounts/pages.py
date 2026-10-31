from django.contrib import messages
from django.db.models import Avg, Count, Q
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django import forms

from bookings.models import Booking, Review
from services.models import Service, ServiceCategory, ServiceProviderService
from .models import ProviderProfile, SiteFeedback, User
from .security import clean_public_text
from . import security


class FeedbackForm(forms.Form):
    rating = forms.ChoiceField(choices=[(5, '5 - Excellent'), (4, '4 - Good'), (3, '3 - Okay'),
                                        (2, '2 - Poor'), (1, '1 - Terrible')])
    comment = forms.CharField(max_length=400, min_length=10)

    def clean_comment(self):
        return clean_public_text(self.cleaned_data['comment'].strip())


ROLE_LABEL = {User.Role.CUSTOMER: 'Customer', User.Role.BUSINESS: 'Business',
              User.Role.SERVICE_PROVIDER: 'Service provider'}


def _first_name(user):
    return user.first_name or user.username


def about(request):
    """Static-looking About page. The numbers and reviews are real, read from the database."""
    providers = ProviderProfile.objects.filter(security.verified_user_q('user__'))
    stats = {
        'providers': providers.count(),
        'services': Service.objects.filter(is_active=True).count(),
        'categories': ServiceCategory.objects.filter(is_active=True).count(),
        'cities': providers.exclude(city='').values('city').distinct().count(),
        'bookings': Booking.objects.exclude(status=Booking.Status.CANCELLED).count(),
    }

    def reviews_by(role):
        items = []
        for fb in SiteFeedback.objects.filter(is_approved=True, role=role).select_related('user')[:3]:
            items.append({'name': _first_name(fb.user), 'rating': fb.rating, 'text': fb.comment,
                          'note': 'About Servana', 'role': ROLE_LABEL[role]})
        if role in (User.Role.CUSTOMER, User.Role.BUSINESS):
            for r in (Review.objects.filter(is_approved=True, customer__user__role=role).exclude(comment='')
                      .select_related('customer__user', 'provider', 'booking__service').order_by('-created_at')[:3]):
                items.append({'name': _first_name(r.customer.user), 'rating': r.rating, 'text': r.comment,
                              'note': f'{r.booking.service.name} by {r.provider.provider_name}',
                              'role': ROLE_LABEL[role]})
        return items[:2]

    top_providers = (ProviderProfile.objects.filter(security.verified_user_q('user__'))
                     .annotate(avg=Avg('received_reviews__rating', filter=Q(received_reviews__is_approved=True)),
                               n=Count('received_reviews', filter=Q(received_reviews__is_approved=True)))
                     .filter(n__gt=0).order_by('-avg', '-n')[:3])

    all_reviews = (reviews_by(User.Role.CUSTOMER) + reviews_by(User.Role.BUSINESS)
                   + reviews_by(User.Role.SERVICE_PROVIDER))
    average = round(sum(r['rating'] for r in all_reviews) / len(all_reviews), 1) if all_reviews else None
    return render(request, 'pages/about.html', {
        'stats': stats, 'all_reviews': all_reviews, 'average': average,
        'top_providers': top_providers,
    })


@login_required
@require_POST
def about_feedback(request):
    user = request.user
    if user.is_superuser or user.role == User.Role.ADMIN:
        messages.info(request, 'Admins do not post reviews.')
        return redirect('about')
    form = FeedbackForm(request.POST)
    if security.too_many(f'feedback:{user.pk}', 3, 86400):
        messages.error(request, 'You can share up to 3 comments a day. Please try again tomorrow.')
        return redirect('about')
    if form.is_valid():
        SiteFeedback.objects.create(user=user, role=user.role, rating=int(form.cleaned_data['rating']),
                                    comment=form.cleaned_data['comment'])
        messages.success(request, 'Thank you! Your comment will appear after an admin approves it.')
    else:
        messages.error(request, ' '.join(e for errs in form.errors.values() for e in errs))
    return redirect('about')
