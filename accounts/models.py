from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.utils import timezone


def private_storage():
    """ID documents are saved outside the public media folder, so nobody can open them by URL."""
    return FileSystemStorage(location=settings.PRIVATE_MEDIA_ROOT)


class User(AbstractUser):

    class Role(models.TextChoices):
        CUSTOMER = 'CUSTOMER', 'Customer'
        SERVICE_PROVIDER = 'SERVICE_PROVIDER', 'Service Provider'
        BUSINESS = 'BUSINESS', 'Business'
        ADMIN = 'ADMIN', 'Admin'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CUSTOMER
    )

    phone_number = models.CharField(
        max_length=20,
        blank=True
    )

    # Trust checks. A person can only book, pay or offer services when all three are True.
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)
    id_verified = models.BooleanField(default=False)     # passport and visa approved by an admin

    def __str__(self):
        return self.username

    @property
    def is_verified(self):
        if self.is_superuser or self.role == self.Role.ADMIN:
            return True
        return bool(self.email_verified and self.phone_verified and self.id_verified and not self.id_expired)

    @property
    def id_expired(self):
        """True when the approved passport or visa has run out since an admin approved it."""
        record = getattr(self, 'identity', None)
        if record is None:
            return False            # older accounts that were trusted before ID checks existed
        today = timezone.localdate()
        return record.passport_expiry <= today or bool(record.visa_expiry and record.visa_expiry <= today)


class CustomerProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='customer_profile'
    )
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    postcode = models.CharField(max_length=10, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - Customer"


class ProviderProfile(models.Model):

    class AvailabilityStatus(models.TextChoices):
        AVAILABLE = 'AVAILABLE', 'Available'
        BUSY = 'BUSY', 'Busy'
        UNAVAILABLE = 'UNAVAILABLE', 'Unavailable'

    class VerificationStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        VERIFIED = 'VERIFIED', 'Verified'
        REJECTED = 'REJECTED', 'Rejected'

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='provider_profile'
    )
    provider_name = models.CharField(max_length=150)
    bio = models.TextField(blank=True)
    experience_years = models.PositiveIntegerField(default=0)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    postcode = models.CharField(max_length=10, blank=True)
    service_area = models.CharField(max_length=200, blank=True)

    availability_status = models.CharField(
        max_length=20,
        choices=AvailabilityStatus.choices,
        default=AvailabilityStatus.AVAILABLE
    )

    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING
    )

    profile_image = models.ImageField(
        upload_to='provider_profiles/',
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.provider_name


class Business(models.Model):

    class VerificationStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        VERIFIED = 'VERIFIED', 'Verified'
        REJECTED = 'REJECTED', 'Rejected'

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='businesses'
    )
    business_name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    postcode = models.CharField(max_length=10, blank=True)
    website = models.URLField(blank=True)

    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.business_name


class IdentityVerification(models.Model):
    """Passport and visa details sent by a user. An admin approves or rejects them."""

    class DocumentType(models.TextChoices):
        NZ_PASSPORT = 'NZ_PASSPORT', 'New Zealand passport'
        OTHER_PASSPORT = 'OTHER_PASSPORT', 'Other passport with a New Zealand visa'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Waiting for admin'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='identity')
    full_name = models.CharField(max_length=150)
    nationality = models.CharField(max_length=80)
    document_type = models.CharField(max_length=20, choices=DocumentType.choices)
    # we keep only a one-way hash of the passport number, to spot one passport used on many accounts
    passport_hash = models.CharField(max_length=64, db_index=True)
    passport_expiry = models.DateField()
    passport_image = models.FileField(upload_to='passports/', storage=private_storage)
    visa_type = models.CharField(max_length=60, blank=True)
    visa_expiry = models.DateField(null=True, blank=True)
    visa_image = models.FileField(upload_to='visas/', storage=private_storage, blank=True)

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    admin_note = models.CharField(max_length=255, blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='reviewed_identities')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"ID check for {self.user.username} ({self.get_status_display()})"


class PhoneCode(models.Model):
    """A 6-digit code sent to a mobile number. Only a hash of the code is stored."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='phone_codes')
    phone = models.CharField(max_length=20)
    code_hash = models.CharField(max_length=64)
    attempts = models.PositiveSmallIntegerField(default=0)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)


class SiteFeedback(models.Model):
    """What a verified user says about Servana itself. Shown on the About page after an admin approves it."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='site_feedback')
    role = models.CharField(max_length=20, choices=User.Role.choices)     # their role when they wrote it
    rating = models.PositiveSmallIntegerField(default=5)
    comment = models.TextField(max_length=400)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username}: {self.rating}/5"
