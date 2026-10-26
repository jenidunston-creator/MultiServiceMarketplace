from django.db import models
from accounts.models import CustomerProfile, ProviderProfile


class ServiceCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'service categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Service(models.Model):
    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.CASCADE,
        related_name='services'
    )
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    base_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class ServiceProviderService(models.Model):
    provider = models.ForeignKey(
        ProviderProfile,
        on_delete=models.CASCADE,
        related_name='offered_services'
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='service_providers'
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    experience_years = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True)
    availability = models.CharField(max_length=150, blank=True)
    image = models.ImageField(
        upload_to='services/',
        blank=True,
        null=True
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['provider', 'service'],
                name='unique_provider_service'
            )
        ]

    def __str__(self):
        return f"{self.provider} - {self.service}"


class ServiceRequest(models.Model):

    class Urgency(models.TextChoices):
        NORMAL = 'NORMAL', 'Normal'
        URGENT = 'URGENT', 'Urgent'
        EMERGENCY = 'EMERGENCY', 'Emergency'

    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        MATCHED = 'MATCHED', 'Matched'
        BOOKED = 'BOOKED', 'Booked'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    customer = models.ForeignKey(
        CustomerProfile,
        on_delete=models.CASCADE,
        related_name='service_requests'
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='service_requests'
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    ai_summary = models.TextField(blank=True)
    location = models.TextField()
    city = models.CharField(max_length=100)
    postcode = models.CharField(max_length=10)
    preferred_date = models.DateField()
    preferred_time = models.TimeField()
    urgency = models.CharField(
        max_length=20,
        choices=Urgency.choices,
        default=Urgency.NORMAL
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.customer.user.username}"


class ProviderMatch(models.Model):

    class Status(models.TextChoices):
        SUGGESTED = 'SUGGESTED', 'Suggested'
        INTERESTED = 'INTERESTED', 'Interested'
        DECLINED = 'DECLINED', 'Declined'

    service_request = models.ForeignKey(
        ServiceRequest,
        on_delete=models.CASCADE,
        related_name='provider_matches'
    )
    provider = models.ForeignKey(
        ProviderProfile,
        on_delete=models.CASCADE,
        related_name='matches'
    )
    match_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    match_reason = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SUGGESTED
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['service_request', 'provider'],
                name='unique_request_provider_match'
            )
        ]

    def __str__(self):
        return f"{self.service_request} - {self.provider}"