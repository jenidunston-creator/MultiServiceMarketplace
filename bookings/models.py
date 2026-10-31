from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from accounts.models import CustomerProfile, ProviderProfile
from services.models import ServiceRequest, Service


class Quotation(models.Model):

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        ACCEPTED = 'ACCEPTED', 'Accepted'
        REJECTED = 'REJECTED', 'Rejected'
        EXPIRED = 'EXPIRED', 'Expired'

    service_request = models.ForeignKey(
        ServiceRequest,
        on_delete=models.CASCADE,
        related_name='quotations'
    )
    provider = models.ForeignKey(
        ProviderProfile,
        on_delete=models.CASCADE,
        related_name='quotations'
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    message = models.TextField(blank=True)
    proposed_date = models.DateField()
    proposed_time = models.TimeField()
    valid_until = models.DateTimeField(
        null=True,
        blank=True
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Quotation #{self.id} - {self.provider}"


class Booking(models.Model):

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        CONFIRMED = 'CONFIRMED', 'Confirmed'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    customer = models.ForeignKey(
        CustomerProfile,
        on_delete=models.CASCADE,
        related_name='bookings'
    )
    provider = models.ForeignKey(
        ProviderProfile,
        on_delete=models.CASCADE,
        related_name='bookings'
    )
    service_request = models.OneToOneField(
        ServiceRequest,
        on_delete=models.CASCADE,
        related_name='booking'
    )
    quotation = models.OneToOneField(
        Quotation,
        on_delete=models.CASCADE,
        related_name='booking',
        null=True,
        blank=True
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='bookings'
    )
    booking_date = models.DateField()
    booking_time = models.TimeField()
    agreed_price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Booking #{self.id} - {self.customer}"


class Payment(models.Model):
    """Money for one booking. Servana (the admin) holds it until the customer confirms the work,
    then the admin releases it to the provider."""

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Not paid'
        PART_HELD = 'PART_HELD', 'Advance paid (held by Servana)'
        HELD = 'HELD', 'Paid (held by Servana)'
        RELEASED = 'RELEASED', 'Released to provider'
        REFUNDED = 'REFUNDED', 'Refunded'
        FAILED = 'FAILED', 'Failed'

    class Plan(models.TextChoices):
        FULL = 'FULL', 'Pay in full now'
        ADVANCE = 'ADVANCE', 'Pay an advance now, the rest after the work'

    class Method(models.TextChoices):
        STRIPE = 'STRIPE', 'Stripe (test mode)'

    booking = models.OneToOneField(
        Booking,
        on_delete=models.CASCADE,
        related_name='payment'
    )
    # total price of the booking
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    plan = models.CharField(max_length=10, choices=Plan.choices, default=Plan.FULL)
    # how much has been paid so far
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    method = models.CharField(
        max_length=10,
        choices=Method.choices,
        default=Method.STRIPE
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    transaction_reference = models.CharField(
        max_length=100,
        blank=True
    )
    paid_at = models.DateTimeField(
        null=True,
        blank=True
    )
    # the customer says the work is done and good
    customer_confirmed_at = models.DateTimeField(null=True, blank=True)
    # set when an admin releases the money to the provider (or refunds it)
    reviewed_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_payments'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    admin_note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment for Booking #{self.booking.id}"

    @property
    def balance_due(self):
        return self.amount - self.amount_paid

    @property
    def fully_paid(self):
        return self.amount_paid >= self.amount

    @property
    def money_held(self):
        return self.status in (self.Status.PART_HELD, self.Status.HELD)


class PaymentTransaction(models.Model):
    """One Stripe payment (an advance, a balance or a full payment)."""

    class Kind(models.TextChoices):
        FULL = 'FULL', 'Full payment'
        ADVANCE = 'ADVANCE', 'Advance'
        BALANCE = 'BALANCE', 'Balance'

    class Status(models.TextChoices):
        CREATED = 'CREATED', 'Started'
        PAID = 'PAID', 'Paid'
        FAILED = 'FAILED', 'Failed'

    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='transactions')
    kind = models.CharField(max_length=10, choices=Kind.choices)
    amount = models.DecimalField(max_digits=10, decimal_places=2)          # in NZD
    stripe_session_id = models.CharField(max_length=120, unique=True)
    stripe_payment_id = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.CREATED)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.get_kind_display()} for Booking #{self.payment.booking_id}"


class Payout(models.Model):
    """Money credited to a provider's Servana account when the admin releases a held payment."""
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name='payout')
    provider = models.ForeignKey(ProviderProfile, on_delete=models.CASCADE, related_name='payouts')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reference = models.CharField(max_length=30, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.reference}: ${self.amount} to {self.provider}"


class Review(models.Model):
    booking = models.OneToOneField(
        Booking,
        on_delete=models.CASCADE,
        related_name='review'
    )
    customer = models.ForeignKey(
        CustomerProfile,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    provider = models.ForeignKey(
        ProviderProfile,
        on_delete=models.CASCADE,
        related_name='received_reviews'
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(blank=True)
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Review for {self.provider} - {self.rating}/5"

    def save(self, *args, **kwargs):
        if not 1 <= self.rating <= 5:
            raise ValueError("Rating must be between 1 and 5.")
        super().save(*args, **kwargs)


class Complaint(models.Model):
    """A complaint about a booking. The customer or the provider can raise it, and an admin answers it."""

    class Category(models.TextChoices):
        QUALITY = 'QUALITY', 'Poor quality of work'
        NO_SHOW = 'NO_SHOW', 'Did not turn up'
        PAYMENT = 'PAYMENT', 'Payment problem'
        BEHAVIOUR = 'BEHAVIOUR', 'Rude or unsafe behaviour'
        OTHER = 'OTHER', 'Something else'

    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        IN_REVIEW = 'IN_REVIEW', 'Being looked at'
        RESOLVED = 'RESOLVED', 'Resolved'
        DISMISSED = 'DISMISSED', 'Dismissed'

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name='complaints'
    )
    raised_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='complaints_made'
    )
    against = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='complaints_received'
    )
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.QUALITY)
    subject = models.CharField(max_length=150)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    admin_response = models.TextField(blank=True)
    handled_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='complaints_handled'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Complaint #{self.pk}: {self.subject}"
