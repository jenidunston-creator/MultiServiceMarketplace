import json
import logging
import uuid
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Avg
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import CustomerProfile, User
from communication.models import Notification
from communication.notify import notify, notify_admins
from services.models import ProviderMatch, ServiceProviderService, ServiceRequest
from . import stripe_client
from .forms import ComplaintForm, QuotationForm, RequestForm, ReviewForm
from .models import Booking, Complaint, Payment, PaymentTransaction, Payout, Quotation, Review

logger = logging.getLogger(__name__)

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
    listing = get_object_or_404(
        ServiceProviderService.objects.select_related('provider__user', 'service', 'service__category'),
        pk=pk, is_active=True,
    )
    if not listing.provider.user.is_verified:      # never book an unverified provider
        raise Http404
    return listing


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
            notify(request.user, Notification.NotificationType.BOOKING, 'Booking placed',
                   f'Your booking for {listing.service.name} on {service_request.preferred_date:%d %b %Y} '
                   f'was sent to the provider. Next: wait for them to confirm, then pay.', '/bookings/')
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
        pay = getattr(b, 'payment', None)
        done = pay is not None and (pay.fully_paid or pay.status in (
            Payment.Status.RELEASED, Payment.Status.REFUNDED))
        b.can_pay = b.status != Booking.Status.CANCELLED and not done
        # the customer can confirm the work once it is complete and fully paid
        b.can_confirm = (pay is not None and pay.status == Payment.Status.HELD
                         and b.status == Booking.Status.COMPLETED and not pay.customer_confirmed_at)

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

    # nobody starts work until the customer has paid (at least the advance) to Servana
    if new_status in (Booking.Status.IN_PROGRESS, Booking.Status.COMPLETED):
        pay = getattr(booking, 'payment', None)
        if not (pay and pay.money_held):
            messages.error(request, 'The customer has not paid yet. Ask them to pay the advance or the full '
                                    'amount first. The money is held safely by Servana until the job is done.')
            return redirect('booking_list')

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
def advance_amount(total):
    """The advance is ADVANCE_PERCENT of the price, rounded to cents."""
    return (total * Decimal(settings.ADVANCE_PERCENT) / 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


# Stripe cannot take very small payments, so a tiny job can only be paid in full.
MIN_PART = Decimal('1.00')


def advance_allowed(total):
    """The advance option is offered only when both the advance and the rest are big enough for Stripe."""
    advance = advance_amount(total)
    return advance >= MIN_PART and (total - advance) >= MIN_PART


def get_payable_booking(request, pk):
    return get_object_or_404(
        Booking.objects.select_related('service', 'provider'), pk=pk, customer__user=request.user)


@role_required(*BUYER_ROLES)
def booking_pay(request, pk):
    booking = get_payable_booking(request, pk)

    if booking.status == Booking.Status.CANCELLED:
        messages.error(request, 'This booking was cancelled, so it cannot be paid.')
        return redirect('booking_list')

    payment = Payment.objects.filter(booking=booking).first()
    if payment and payment.status in (Payment.Status.RELEASED, Payment.Status.REFUNDED):
        messages.info(request, 'This booking is already settled.')
        return redirect('booking_list')
    if payment and payment.fully_paid:
        messages.info(request, 'This booking is already paid in full. Servana is holding the money.')
        return redirect('booking_list')

    total = booking.agreed_price
    subtotal = (total / Decimal('1.15')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    paying_balance = bool(payment and payment.money_held)          # the advance is already paid
    return render(request, 'bookings/payment.html', {
        'booking': booking, 'payment': payment, 'paying_balance': paying_balance,
        'total': total, 'subtotal': subtotal, 'gst': total - subtotal,
        'advance': advance_amount(total), 'advance_rest': total - advance_amount(total),
        'advance_ok': advance_allowed(total),
        'advance_percent': settings.ADVANCE_PERCENT,
        'balance': payment.balance_due if paying_balance else None,
        'stripe_ready': stripe_client.is_configured(),
    })


@role_required(*BUYER_ROLES)
@require_POST
def payment_create_order(request, pk):
    """Step 1: start a Stripe Checkout. We decide the amount here, never the browser."""
    booking = get_payable_booking(request, pk)
    if booking.status == Booking.Status.CANCELLED:
        return JsonResponse({'error': 'This booking was cancelled.'}, status=400)
    if not stripe_client.is_configured():
        return JsonResponse({'error': 'Payments are not set up yet (the Stripe test key is missing).'}, status=503)

    try:
        plan = json.loads(request.body or '{}').get('plan', 'FULL')
    except ValueError:
        plan = 'FULL'

    with transaction.atomic():
        payment, _ = Payment.objects.select_for_update().get_or_create(
            booking=booking, defaults={'amount': booking.agreed_price})
        if payment.status in (Payment.Status.RELEASED, Payment.Status.REFUNDED) or payment.fully_paid:
            return JsonResponse({'error': 'This booking is already paid.'}, status=400)

        if payment.money_held:                       # the advance is paid, now the balance
            kind, amount = PaymentTransaction.Kind.BALANCE, payment.balance_due
        elif plan == Payment.Plan.ADVANCE and advance_allowed(payment.amount):
            kind, amount = PaymentTransaction.Kind.ADVANCE, advance_amount(payment.amount)
            payment.plan = Payment.Plan.ADVANCE
        else:
            kind, amount = PaymentTransaction.Kind.FULL, payment.amount
            payment.plan = Payment.Plan.FULL
        payment.save()

        # an older checkout that was never finished must not stay open, or the customer could pay twice
        for old in payment.transactions.filter(status=PaymentTransaction.Status.CREATED):
            try:
                stripe_client.expire_session(old.stripe_session_id)
            except Exception:
                # it may already be paid; the return page still counts it safely
                logger.warning('Could not close old checkout %s', old.stripe_session_id)
            else:
                old.status = PaymentTransaction.Status.FAILED
                old.save()

        label = {'FULL': 'full payment', 'ADVANCE': 'advance', 'BALANCE': 'balance'}[kind]
        return_url = request.build_absolute_uri(reverse('payment_return', args=[booking.pk]))
        try:
            session = stripe_client.create_checkout_session(
                amount, f'{booking.service.name} ({label}) - Servana booking #{booking.pk}',
                success_url=return_url + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=request.build_absolute_uri(reverse('booking_pay', args=[booking.pk])),
                metadata={'booking': booking.pk, 'kind': kind},
                customer_email=request.user.email)
        except Exception:                           # network problem, wrong key, and so on
            logger.exception('Stripe session failed')
            return JsonResponse({'error': 'Could not start the payment. Please try again.'}, status=502)

        PaymentTransaction.objects.create(
            payment=payment, kind=kind, amount=amount, stripe_session_id=session['id'])

    return JsonResponse({'url': session['url']})


@role_required(*BUYER_ROLES)
def payment_return(request, pk):
    """Step 2: Stripe sends the customer back here. We ask Stripe directly if the payment really happened."""
    booking = get_payable_booking(request, pk)
    session_id = request.GET.get('session_id', '')

    with transaction.atomic():
        txn = (PaymentTransaction.objects.select_for_update()
               .select_related('payment').filter(stripe_session_id=session_id, payment__booking=booking).first())
        if txn is None:
            messages.error(request, 'We could not find that payment.')
            return redirect('booking_list')
        if txn.status == PaymentTransaction.Status.PAID:          # already counted, do nothing
            return redirect('booking_list')

        try:
            session = stripe_client.retrieve_session(session_id)
        except Exception:
            logger.exception('Stripe lookup failed')
            messages.error(request, 'We could not confirm the payment with Stripe. If money was taken, contact us.')
            return redirect('booking_list')

        genuine = (session.get('payment_status') == 'paid'
                   and session.get('amount_total') == stripe_client.to_cents(txn.amount)
                   and session.get('currency') == 'nzd'
                   and str(session.get('metadata', {}).get('booking')) == str(booking.pk))
        if not genuine:
            messages.error(request, 'The payment was not completed, so nothing was charged. You can try again.')
            return redirect('booking_pay', pk=booking.pk)

        now = timezone.now()
        txn.status = PaymentTransaction.Status.PAID
        txn.stripe_payment_id = str(session.get('payment_intent') or session_id)
        txn.paid_at = now
        txn.save()

        payment = txn.payment
        # Never count more than the price. If the customer paid twice (two checkout tabs), only the
        # amount still due is counted and the extra is flagged for the admin to refund in Stripe.
        settled = payment.status in (Payment.Status.RELEASED, Payment.Status.REFUNDED)
        credit = Decimal('0') if settled else min(txn.amount, max(payment.balance_due, Decimal('0')))
        extra = txn.amount - credit
        payment.amount_paid += credit
        payment.transaction_reference = txn.stripe_payment_id
        payment.paid_at = now
        if not settled:
            payment.status = Payment.Status.HELD if payment.fully_paid else Payment.Status.PART_HELD
        payment.save()

    if extra > 0:
        notify_admins(Notification.NotificationType.PAYMENT, 'Extra payment to refund',
                      f'Booking #{booking.pk}: the customer paid ${extra} more than the price (a second checkout). '
                      f'Please refund ${extra} in the Stripe dashboard.', '/bookings/payments/')
        messages.warning(request, f'You paid ${extra} more than needed. Servana will refund the extra ${extra}.')
    if credit > 0:
        notify(booking.provider.user, Notification.NotificationType.PAYMENT, 'Payment received by Servana',
               f'{request.user.username} paid ${credit} for booking #{booking.pk} ({booking.service.name}). '
               f'Servana holds it safely, so you can start the work.', '/bookings/')
        notify(request.user, Notification.NotificationType.PAYMENT, 'Payment received',
               f'We received your ${credit} for booking #{booking.pk} ({booking.service.name}). '
               + ('It is held safely until the work is done.' if payment.fully_paid
                  else f'This was the advance. ${payment.balance_due} is still due before the work is finished.'),
               '/bookings/')
        notify_admins(Notification.NotificationType.PAYMENT, 'Payment held',
                      f'${credit} for booking #{booking.pk} is now held by Servana.', '/bookings/payments/')
        messages.success(request, f'Payment of ${credit} received. Servana is holding it safely until the work is done.')
    return redirect('booking_list')


@role_required(*BUYER_ROLES)
@require_POST
def payment_confirm_work(request, pk):
    """The customer says the work is done and good. Now the admin can release the money."""
    booking = get_payable_booking(request, pk)
    payment = Payment.objects.filter(booking=booking).first()
    if not (payment and payment.status == Payment.Status.HELD and booking.status == Booking.Status.COMPLETED):
        messages.error(request, 'You can confirm once the job is completed and fully paid.')
        return redirect('booking_list')
    if not payment.customer_confirmed_at:
        payment.customer_confirmed_at = timezone.now()
        payment.save()
        notify_admins(Notification.NotificationType.PAYMENT, 'Release payment',
                      f'The customer confirmed booking #{booking.pk}. Please release ${payment.amount} to the provider.',
                      '/bookings/payments/')
        notify(booking.provider.user, Notification.NotificationType.PAYMENT, 'Work confirmed',
               f'The customer confirmed booking #{booking.pk}. Servana will release your payment soon.', '/bookings/')
    messages.success(request, 'Thank you! Servana will now release the payment to the provider.')
    return redirect('booking_list')


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


# ------------------------------------------------------------------ admin: held payments
@role_required(User.Role.ADMIN)
def payment_approvals(request):
    payments = Payment.objects.select_related(
        'booking__service', 'booking__customer__user', 'booking__provider', 'reviewed_by')
    held = payments.filter(status__in=[Payment.Status.HELD, Payment.Status.PART_HELD])
    return render(request, 'bookings/payment_approvals.html', {
        'ready': held.filter(status=Payment.Status.HELD, customer_confirmed_at__isnull=False).order_by('customer_confirmed_at'),
        'holding': held.exclude(status=Payment.Status.HELD, customer_confirmed_at__isnull=False).order_by('created_at'),
        'history': payments.filter(status__in=[Payment.Status.RELEASED, Payment.Status.REFUNDED]
                                   ).order_by('-reviewed_at')[:30],
    })


def refund_with_stripe(payment):
    """Sends the customer's money back through Stripe (test mode). Returns (True, '') when done,
    or (False, 'what went wrong'). Already refunded parts are remembered, so trying again is safe."""
    todo = list(payment.transactions.filter(status=PaymentTransaction.Status.PAID))
    if not todo:
        return True, ''                       # nothing was paid through Stripe (older records)
    if not stripe_client.is_configured():
        return False, 'Stripe is not set up here (the test key is missing), so the refund cannot be sent.'
    for txn in todo:
        if not txn.stripe_payment_id.startswith('pi_'):
            return False, f'Payment part ${txn.amount} has no Stripe reference. Refund it in the Stripe dashboard.'
        try:
            refund = stripe_client.create_refund(txn.stripe_payment_id, f'servana-refund-txn-{txn.pk}')
        except Exception as error:
            code = ''
            try:
                code = error.response.json().get('error', {}).get('code', '')
            except Exception:
                pass
            if code != 'charge_already_refunded':
                logger.exception('Stripe refund failed')
                return False, (f'Stripe could not refund ${txn.amount}. The payment is still held, '
                               f'so you can try again.')
            refund = {'id': 'already-refunded'}
        txn.status = PaymentTransaction.Status.REFUNDED
        txn.stripe_refund_id = str(refund.get('id', ''))[:120]
        txn.save()
    return True, ''


@role_required(User.Role.ADMIN)
@require_POST
def payment_decide(request, pk):
    payment = get_object_or_404(Payment.objects.select_related(
        'booking__customer__user', 'booking__provider__user', 'booking__service'), pk=pk)
    if not payment.money_held:
        messages.info(request, 'That payment is not being held any more.')
        return redirect('payment_approvals')

    decision = request.POST.get('decision')
    note = request.POST.get('note', '').strip()[:255]
    booking = payment.booking
    if decision == 'release':
        # the money only goes to the provider after the customer confirmed the finished work
        if payment.status != Payment.Status.HELD or not payment.customer_confirmed_at:
            messages.error(request, 'The customer has not confirmed the work yet, so the money stays held.')
            return redirect('payment_approvals')
        payment.status = Payment.Status.RELEASED
        # credit the provider's Servana account (one payout per payment)
        payout, _ = Payout.objects.get_or_create(
            payment=payment,
            defaults={'provider': booking.provider, 'amount': payment.amount_paid,
                      'reference': 'PAYOUT-' + uuid.uuid4().hex[:10].upper()})
        text_customer = f'Servana released your payment for booking #{booking.pk} to the provider. Thank you!'
        text_provider = (f'${payout.amount} for booking #{booking.pk} ({booking.service.name}) was credited '
                         f'to your Servana account. Reference {payout.reference}.')
    elif decision == 'refund':
        done, problem = refund_with_stripe(payment)
        if not done:
            messages.error(request, problem)
            return redirect('payment_approvals')
        payment.status = Payment.Status.REFUNDED
        text_customer = (f'Your payment for booking #{booking.pk} was refunded to your card through Stripe. '
                         f'It can take a few days to show on your statement.'
                         + (f' Note: {note}' if note else ''))
        text_provider = f'The payment for booking #{booking.pk} was refunded to the customer.'
    else:
        messages.error(request, 'Please choose release or refund.')
        return redirect('payment_approvals')

    payment.reviewed_by = request.user
    payment.reviewed_at = timezone.now()
    payment.admin_note = note
    payment.save()

    notify(booking.customer.user, Notification.NotificationType.PAYMENT,
           'Payment ' + ('released' if decision == 'release' else 'refunded'), text_customer, '/bookings/')
    notify(booking.provider.user, Notification.NotificationType.PAYMENT,
           'Payment ' + ('released' if decision == 'release' else 'refunded'), text_provider, '/bookings/')
    messages.success(request, f'Payment #{payment.pk}: {payment.get_status_display().lower()}.'
                     + (' The money was sent back through Stripe.' if decision == 'refund' else ''))
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
