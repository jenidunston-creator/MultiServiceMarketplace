from django.contrib import admin
from .models import Quotation, Booking, Payment, PaymentTransaction, Payout, Review, Complaint


@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = ('id', 'service_request', 'provider', 'amount', 'status', 'created_at')
    list_filter = ('status',)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'customer', 'provider', 'service',
        'booking_date', 'agreed_price', 'status',
    )
    list_filter = ('status', 'booking_date')
    search_fields = ('customer__user__username', 'provider__provider_name')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'booking', 'amount', 'plan', 'amount_paid', 'status', 'customer_confirmed_at', 'reviewed_by')
    list_filter = ('status', 'plan')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'provider', 'customer', 'rating', 'is_approved', 'created_at')
    list_filter = ('is_approved', 'rating')
    list_editable = ('is_approved',)
    search_fields = ('provider__provider_name', 'comment')


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ('id', 'subject', 'booking', 'raised_by', 'against', 'category', 'status', 'created_at')
    list_filter = ('status', 'category')
    search_fields = ('subject', 'description', 'raised_by__username')


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'payment', 'kind', 'amount', 'status', 'stripe_session_id', 'paid_at')
    list_filter = ('status', 'kind')


@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = ('reference', 'provider', 'amount', 'payment', 'created_at')
    search_fields = ('reference', 'provider__provider_name')
