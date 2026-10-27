import uuid
from decimal import Decimal, ROUND_HALF_UP

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Avg
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import CustomerProfile, User
from communication.models import Notification
from communication.notify import notify, notify_admins
from services.models import ProviderMatch, ServiceProviderService, ServiceRequest
from .forms import ComplaintForm, PaymentForm, QuotationForm, RequestForm, ReviewForm
from .models import Booking, Complaint, Payment, Quotation, Review

# these two roles can book services; providers and admins cannot
BUYER_ROLES = (User.Role.CUSTOMER, User.Role.BUSINESS)


# ------------------------------------------------------------------ helpers
def is_admin(user):
    return user.is_superuser or user.role == User.Role.ADMIN


def customer_profile(user):
    """Get the customer's profile (make one if it is missing)."""
    profile, _ = CustomerProfile.objects.get_or_create(user=user)
    return profile


def get_active_listing(pk):
    return get_object_or_404(
        ServiceProviderService.objects.select_related('provider', 'service', 'service__category'),
        pk=pk, is_active=True,
    )


def save_request(form, profile, listing):
    """Turn the filled-in form into a ServiceRequest."""
    service_request = form.save(commit=False)
    service_request.customer = profile
    service_request.service = listing.service
    service_request.title = listing.service.name
    return service_request


# ------------------------------------------------------------------ bookings
@role_required(*BUYER_ROLES)
def booking_create(request):
    """Book now: creates the request and the booking in one go."""
    listing = get_active_listing(request.GET.get('service') or request.POST.get('service') or 0)

    if listing.provider.user_id == request.user.id:
        raise PermissionDenied          # you cannot book your own service

    profile = customer_profile(request.user)

    if request.method == 'POST':
        form = RequestForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                service_request = save_request(form, profile, listing)
                service_request.status = ServiceRequest.Status.BOOKED
                service_request.save()
                Booking.objects.create(
                    customer=profile,
                    provider=listing.provider,
                    service_request=service_request,
                    service=listing.service,
                    booking_date=service_request.preferred_date,
                    booking_time=service_request.preferred_time,
                    agreed_price=listing.price,
                    notes=service_request.description,
                )
            notify(listing.provider.user, Notification.NotificationType.BOOKING, 'New booking',
                   f'{request.user.username} booked {listing.service.name} for '
                   f'{service_request.preferred_date:%d %b %Y}.', '/bookings/')
            messages.success(request, 'Booking sent! The provider will confirm it soon.')
            return redirect('booking_list')
    else:
        form = RequestForm(initial={'city': listing.provider.city})

    return render(request, 'bookings/booking_form.html', {
        'form': form, 'listing': listing, 'mode': 'book'})


@role_required(User.Role.CUSTOMER, User.Role.BUSINESS, User.Role.SERVICE_PROVIDER, User.Role.ADMIN)
def booking_list(request):
    bookings = Booking.objects.select_related(
        'service', 'customer__user', 'provider', 'payment', 'review'
    ).order_by('-created_at')

    if is_admin(request.user):
        view_as = 'admin'
    elif request.user.role == User.Role.SERVICE_PROVIDER:
        view_as = 'provider'
        bookings = bookings.filter(provider__user=request.user)
    else:
        view_as = 'customer'
        bookings = bookings.filter(customer__user=request.user)

    bookings = list(bookings)
    for b in bookings:
        locked = hasattr(b, 'payment') and b.payment.status in (
            Payment.Status.PAID, Payment.Status.AWAITING)
        b.can_pay = b.status != Booking.Status.CANCELLED and not locked

    return render(request, 'bookings/booking_list.html', {
        'bookings': bookings,
        'view_as': view_as,
        'provider_choices': [(Booking.Status.CONFIRMED, 'Confirmed'),
                             (Booking.Status.IN_PROGRESS, 'In progress'),
                             (Booking.Status.COMPLETED, 'Completed'),
                             (Booking.Status.CANCELLED, 'Cancelled')],
    })


@role_required(User.Role.CUSTOMER, User.Role.BUSINESS, User.Role.SERVICE_PROVIDER, User.Role.ADMIN)
@require_POST
def booking_status(request, pk):
    """Provider updates the job status. Customer can only cancel."""
    booking = get_object_or_404(Booking, pk=pk)
    new_status = request.POST.get('status')
    allowed = {Booking.Status.CONFIRMED, Booking.Status.IN_PROGRESS,
               Booking.Status.COMPLETED, Booking.Status.CANCELLED}
    if new_status not in allowed:
        messages.error(request, 'That status is not valid.')
        return redirect('booking_list')

    user = request.user
    if is_admin(user) or booking.provider.user_id == user.id:
        pass                                            # provider / admin: any status
    elif booking.customer.user_id == user.id:           # customer: cancel only
        if new_status != Booking.Status.CANCELLED or booking.status not in (
                Booking.Status.PENDING, Booking.Status.CONFIRMED):
            raise PermissionDenied
    else:
        raise PermissionDenied

    booking.status = new_status
    booking.save()

    # keep the original request in step with the booking
    if new_status == Booking.Status.CANCELLED:
        booking.service_request.status = ServiceRequest.Status.CANCELLED
        booking.service_request.save()
    elif new_status == Booking.Status.COMPLETED:
        booking.service_request.status = ServiceRequest.Status.COMPLETED
        booking.service_request.save()

    # tell the other person
    text = f'Booking #{booking.pk} ({booking.service.name}) is now {booking.get_status_display()}.'
    if booking.customer.user_id == user.id:
        notify(booking.provider.user, Notification.NotificationType.BOOKING, 'Booking updated', text, '/bookings/')
    else:
        notify(booking.customer.user, Notification.NotificationType.BOOKING, 'Booking updated', text, '/bookings/')

    messages.success(request, f'Booking #{booking.pk} is now {booking.get_status_display()}.')
    return redirect('booking_list')


# ------------------------------------------------------------------ payment
@role_required(*BUYER_ROLES)
def booking_pay(request, pk):
    booking = get_object_or_404(
        Booking.objects.select_related('service', 'provider'), pk=pk, customer__user=request.user)

    if booking.status == Booking.Status.CANCELLED:
        messages.error(request, 'This booking was cancelled, so it cannot be paid.')
        return redirect('booking_list')

    payment = Payment.objects.filter(booking=booking).first()
    if payment and payment.status == Payment.Status.PAID:
        messages.info(request, 'This booking is already paid.')
        return redirect('booking_list')
    if payment and payment.status == Payment.Status.AWAITING:
        messages.info(request, 'Your payment is waiting for admin approval.')
        return redirect('booking_list')

    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            method = form.cleaned_data['method']
            payment = payment or Payment(booking=booking)
            payment.amount = booking.agreed_price
            payment.method = method
            if method == Payment.Method.CASH:
                payment.status = Payment.Status.PENDING      # paid after the job
                payment.paid_at = None
                text = 'You chose to pay the provider after the job.'
            else:
                # demo only, no real card details. An admin must approve it before it counts as paid.
                payment.status = Payment.Status.AWAITING
                payment.paid_at = None
                payment.reviewed_by = None
                payment.reviewed_at = None
                payment.admin_note = ''
                payment.transaction_reference = 'DEMO-' + uuid.uuid4().hex[:10].upper()
                text = 'Payment submitted. It is waiting for admin approval.'
            payment.save()
            if payment.status == Payment.Status.AWAITING:
                notify_admins(Notification.NotificationType.PAYMENT, 'Payment to approve',
                              f'{request.user.username} paid ${payment.amount} for booking #{booking.pk}.',
                              '/bookings/payments/')
            notify(booking.provider.user, Notification.NotificationType.PAYMENT, 'Payment update',
                   f'{request.user.username} chose {payment.get_method_display()} for booking #{booking.pk} '
                   f'({payment.get_status_display()}).', '/bookings/')
            messages.success(request, text)
            return redirect('booking_list')
    else:
        form = PaymentForm()

    total = booking.agreed_price
    subtotal = (total / Decimal('1.15')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return render(request, 'bookings/payment.html', {
        'booking': booking, 'form': form,
        'total': total, 'subtotal': subtotal, 'gst': total - subtotal})


# ------------------------------------------------------------------ reviews
@role_required(*BUYER_ROLES)
def booking_review(request, pk):
    booking = get_object_or_404(
        Booking.objects.select_related('service', 'provider'), pk=pk, customer__user=request.user)

    if booking.status != Booking.Status.COMPLETED:
        messages.error(request, 'You can review a booking after it is completed.')
        return redirect('booking_list')
    if Review.objects.filter(booking=booking).exists():
        messages.info(request, 'You have already reviewed this booking.')
        return redirect('booking_list')

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.booking = booking
            review.customer = booking.customer
            review.provider = booking.provider
            review.save()
            notify(booking.provider.user, Notification.NotificationType.REVIEW, 'New review',
                   f'You received a {review.rating}/5 review for {booking.service.name}.', '/dashboard/provider/')
            messages.success(request, 'Thanks for your review!')
            return redirect('booking_list')
    else:
        form = ReviewForm()

    return render(request, 'bookings/review_form.html', {'form': form, 'booking': booking})


# ------------------------------------------------------------------ quotations
@role_required(*BUYER_ROLES)
def quote_request(request, listing_pk):
    """Customer asks one provider for a quote."""
    listing = get_active_listing(listing_pk)
    if listing.provider.user_id == request.user.id:
        raise PermissionDenied
    profile = customer_profile(request.user)

    if request.method == 'POST':
        form = RequestForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                service_request = save_request(form, profile, listing)
                service_request.status = ServiceRequest.Status.OPEN
                service_request.save()
                ProviderMatch.objects.create(
                    service_request=service_request, provider=listing.provider,
                    status=ProviderMatch.Status.SUGGESTED,
                    match_reason='Customer asked this provider for a quote.')
            notify(listing.provider.user, Notification.NotificationType.SERVICE_REQUEST, 'New quote request',
                   f'{request.user.username} asked for a quote for {listing.service.name}.', '/quotations/')
            messages.success(request, 'Quote request sent. You will see the reply on this page.')
            return redirect('quotation_list')
    else:
        form = RequestForm(initial={'city': listing.provider.city})

    return render(request, 'bookings/booking_form.html', {
        'form': form, 'listing': listing, 'mode': 'quote'})


@role_required(User.Role.CUSTOMER, User.Role.BUSINESS, User.Role.SERVICE_PROVIDER, User.Role.ADMIN)
def quotation_list(request):
    context = {'quote_form': QuotationForm()}

    if is_admin(request.user):
        context['view_as'] = 'admin'
        context['quotations'] = Quotation.objects.select_related(
            'service_request__service', 'provider').order_by('-created_at')

    elif request.user.role == User.Role.SERVICE_PROVIDER:
        context['view_as'] = 'provider'
        context['quotations'] = Quotation.objects.filter(
            provider__user=request.user).select_related(
            'service_request__service', 'service_request__customer__user').order_by('-created_at')
        # requests sent to me that I have not answered yet
        context['incoming'] = ServiceRequest.objects.filter(
            provider_matches__provider__user=request.user,
            status=ServiceRequest.Status.OPEN,
        ).exclude(quotations__provider__user=request.user).select_related(
            'service', 'customer__user').order_by('-created_at')

    else:
        context['view_as'] = 'customer'
        context['quotations'] = Quotation.objects.filter(
            service_request__customer__user=request.user).select_related(
            'service_request__service', 'provider').order_by('-created_at')
        context['waiting'] = ServiceRequest.objects.filter(
            customer__user=request.user, status=ServiceRequest.Status.OPEN,
            quotations__isnull=True).select_related('service').order_by('-created_at')

    return render(request, 'bookings/quotation_list.html', context)


@role_required(User.Role.SERVICE_PROVIDER)
@require_POST
def quotation_send(request, request_pk):
    service_request = get_object_or_404(
        ServiceRequest, pk=request_pk, status=ServiceRequest.Status.OPEN,
        provider_matches__provider__user=request.user)

    if Quotation.objects.filter(service_request=service_request,
                                provider__user=request.user).exists():
        messages.info(request, 'You already sent a quote for this request.')
        return redirect('quotation_list')

    form = QuotationForm(request.POST)
    if form.is_valid():
        quotation = form.save(commit=False)
        quotation.service_request = service_request
        quotation.provider = request.user.provider_profile
        quotation.save()
        notify(service_request.customer.user, Notification.NotificationType.QUOTATION, 'You received a quote',
               f'{quotation.provider.provider_name} quoted ${quotation.amount} for {service_request.service.name}.',
               '/quotations/')
        messages.success(request, 'Quote sent to the customer.')
    else:
        messages.error(request, 'Please check the quote: ' + ' '.join(
            e for errs in form.errors.values() for e in errs))
    return redirect('quotation_list')


@role_required(*BUYER_ROLES)
@require_POST
def quotation_accept(request, pk):
    quotation = get_object_or_404(
        Quotation.objects.select_related('service_request', 'provider'),
        pk=pk, service_request__customer__user=request.user)
    service_request = quotation.service_request

    if quotation.status != Quotation.Status.PENDING or \
            service_request.status != ServiceRequest.Status.OPEN:
        messages.error(request, 'This quote can no longer be accepted.')
        return redirect('quotation_list')
    if quotation.valid_until and quotation.valid_until < timezone.now():
        quotation.status = Quotation.Status.EXPIRED
        quotation.save()
        messages.error(request, 'This quote has expired.')
        return redirect('quotation_list')

    with transaction.atomic():
        quotation.status = Quotation.Status.ACCEPTED
        quotation.save()
        service_request.quotations.exclude(pk=quotation.pk).filter(
            status=Quotation.Status.PENDING).update(status=Quotation.Status.REJECTED)
        service_request.status = ServiceRequest.Status.BOOKED
        service_request.save()
        Booking.objects.create(
            customer=service_request.customer,
            provider=quotation.provider,
            service_request=service_request,
            quotation=quotation,
            service=service_request.service,
            booking_date=quotation.proposed_date,
            booking_time=quotation.proposed_time,
            agreed_price=quotation.amount,
            status=Booking.Status.CONFIRMED,
            notes=service_request.description,
        )
    notify(quotation.provider.user, Notification.NotificationType.QUOTATION, 'Quote accepted',
           f'{request.user.username} accepted your quote for {service_request.service.name}.', '/bookings/')
    messages.success(request, 'Quote accepted and booking created.')
    return redirect('booking_list')


@role_required(*BUYER_ROLES)
@require_POST
def quotation_decline(request, pk):
    quotation = get_object_or_404(
        Quotation, pk=pk, service_request__customer__user=request.user,
        status=Quotation.Status.PENDING)
    quotation.status = Quotation.Status.REJECTED
    quotation.save()
    notify(quotation.provider.user, Notification.NotificationType.QUOTATION, 'Quote declined',
           f'{request.user.username} declined your quote for {quotation.service_request.service.name}.',
           '/quotations/')
    messages.info(request, 'Quote declined.')
    return redirect('quotation_list')


# ------------------------------------------------------------------ admin: payment approval
@role_required(User.Role.ADMIN)
def payment_approvals(request):
    payments = Payment.objects.select_related(
        'booking__service', 'booking__customer__user', 'booking__provider', 'reviewed_by')
    return render(request, 'bookings/payment_approvals.html', {
        'waiting': payments.filter(status=Payment.Status.AWAITING).order_by('created_at'),
        'history': payments.exclude(status__in=[Payment.Status.AWAITING, Payment.Status.PENDING]
                                    ).order_by('-reviewed_at', '-created_at')[:30],
    })


@role_required(User.Role.ADMIN)
@require_POST
def payment_decide(request, pk):
    payment = get_object_or_404(Payment.objects.select_related(
        'booking__customer__user', 'booking__provider__user', 'booking__service'), pk=pk)
    if payment.status != Payment.Status.AWAITING:
        messages.info(request, 'That payment has already been decided.')
        return redirect('payment_approvals')

    decision = request.POST.get('decision')
    note = request.POST.get('note', '').strip()[:255]
    booking = payment.booking
    if decision == 'approve':
        payment.status = Payment.Status.PAID
        payment.paid_at = timezone.now()
        text_customer = f'Your payment for booking #{booking.pk} was approved.'
        text_provider = f'The payment for booking #{booking.pk} ({booking.service.name}) was approved.'
    elif decision == 'reject':
        payment.status = Payment.Status.REJECTED
        payment.paid_at = None
        text_customer = (f'Your payment for booking #{booking.pk} was rejected.'
                         + (f' Reason: {note}' if note else ' Please try again.'))
        text_provider = None
    else:
        messages.error(request, 'Please choose approve or reject.')
        return redirect('payment_approvals')

    payment.reviewed_by = request.user
    payment.reviewed_at = timezone.now()
    payment.admin_note = note
    payment.save()

    notify(booking.customer.user, Notification.NotificationType.PAYMENT,
           'Payment ' + ('approved' if decision == 'approve' else 'rejected'), text_customer, '/bookings/')
    if text_provider:
        notify(booking.provider.user, Notification.NotificationType.PAYMENT,
               'Payment approved', text_provider, '/bookings/')
    messages.success(request, f'Payment #{payment.pk} {payment.get_status_display().lower()}.')
    return redirect('payment_approvals')


# ------------------------------------------------------------------ complaints
@role_required(User.Role.CUSTOMER, User.Role.BUSINESS, User.Role.SERVICE_PROVIDER)
def complaint_create(request, pk):
    """The customer or the provider of a booking can raise a complaint about the other person."""
    booking = get_object_or_404(Booking.objects.select_related(
        'customer__user', 'provider__user', 'service'), pk=pk)
    if request.user.id == booking.customer.user_id:
        other = booking.provider.user
    elif request.user.id == booking.provider.user_id:
        other = booking.customer.user
    else:
        raise PermissionDenied

    if request.method == 'POST':
        form = ComplaintForm(request.POST)
        if form.is_valid():
            complaint = form.save(commit=False)
            complaint.booking = booking
            complaint.raised_by = request.user
            complaint.against = other
            complaint.save()
            notify_admins(Notification.NotificationType.GENERAL, 'New complaint',
                          f'{request.user.username} raised a complaint about booking #{booking.pk}: '
                          f'{complaint.subject}', '/bookings/complaints/')
            notify(other, Notification.NotificationType.GENERAL, 'A complaint was raised',
                   f'A complaint was raised about booking #{booking.pk}. An admin will look into it.',
                   '/bookings/complaints/')
            messages.success(request, 'Your complaint was sent. An admin will review it.')
            return redirect('complaint_list')
    else:
        form = ComplaintForm()
    return render(request, 'bookings/complaint_form.html', {'form': form, 'booking': booking, 'other': other})


@role_required(User.Role.CUSTOMER, User.Role.BUSINESS, User.Role.SERVICE_PROVIDER, User.Role.ADMIN)
def complaint_list(request):
    complaints = Complaint.objects.select_related(
        'booking__service', 'raised_by', 'against', 'handled_by')
    if is_admin(request.user):
        status = request.GET.get('status', '')
        if status in Complaint.Status.values:
            complaints = complaints.filter(status=status)
        return render(request, 'bookings/complaint_list.html', {
            'view_as': 'admin', 'complaints': complaints, 'selected_status': status,
            'status_choices': Complaint.Status.choices})
    return render(request, 'bookings/complaint_list.html', {
        'view_as': 'user',
        'made': complaints.filter(raised_by=request.user),
        'received': complaints.filter(against=request.user)})


@role_required(User.Role.ADMIN)
@require_POST
def complaint_respond(request, pk):
    complaint = get_object_or_404(Complaint.objects.select_related('raised_by', 'against'), pk=pk)
    status = request.POST.get('status')
    response = request.POST.get('response', '').strip()
    if status not in Complaint.Status.values:
        messages.error(request, 'Please choose a valid status.')
        return redirect('complaint_list')
    if status in (Complaint.Status.RESOLVED, Complaint.Status.DISMISSED) and not response:
        messages.error(request, 'Please write a short reply before you resolve or dismiss a complaint.')
        return redirect('complaint_list')

    complaint.status = status
    complaint.admin_response = response
    complaint.handled_by = request.user
    complaint.save()
    for person in (complaint.raised_by, complaint.against):
        notify(person, Notification.NotificationType.GENERAL, 'Complaint updated',
               f'Complaint #{complaint.pk} ({complaint.subject}) is now: {complaint.get_status_display()}.',
               '/bookings/complaints/')
    messages.success(request, f'Complaint #{complaint.pk} updated.')
    return redirect('complaint_list')
