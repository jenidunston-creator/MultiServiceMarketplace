from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    User,
    CustomerProfile,
    ProviderProfile,
    Business,
    SiteFeedback,
    IdentityVerification,
)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Servana details', {'fields': ('role', 'phone_number')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Servana details', {'fields': ('role', 'phone_number')}),
    )
    list_display = ('username', 'email', 'role', 'is_staff', 'is_active')
    list_filter = UserAdmin.list_filter + ('role',)


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'city', 'postcode', 'created_at')
    search_fields = ('user__username', 'city')


@admin.register(ProviderProfile)
class ProviderProfileAdmin(admin.ModelAdmin):
    list_display = (
        'provider_name', 'user', 'city',
        'availability_status', 'verification_status',
    )
    list_filter = ('verification_status', 'availability_status', 'city')
    search_fields = ('provider_name', 'user__username', 'city')


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ('business_name', 'owner', 'city', 'verification_status')
    list_filter = ('verification_status', 'city')
    search_fields = ('business_name', 'owner__username')


@admin.register(SiteFeedback)
class SiteFeedbackAdmin(admin.ModelAdmin):
    """Tick 'is approved' to show a comment on the About page."""
    list_display = ('user', 'role', 'rating', 'comment', 'is_approved', 'created_at')
    list_filter = ('is_approved', 'role')
    list_editable = ('is_approved',)


@admin.register(IdentityVerification)
class IdentityVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'status', 'passport_expiry', 'visa_expiry', 'submitted_at')
    list_filter = ('status',)
    exclude = ('passport_image', 'visa_image')
