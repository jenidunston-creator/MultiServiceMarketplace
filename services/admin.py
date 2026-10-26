from django.contrib import admin
from .models import (
    ServiceCategory,
    Service,
    ServiceProviderService,
    ServiceRequest,
    ProviderMatch,
)


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'base_price', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('name',)


@admin.register(ServiceProviderService)
class ServiceProviderServiceAdmin(admin.ModelAdmin):
    list_display = ('provider', 'service', 'price', 'experience_years', 'is_active')
    list_filter = ('is_active', 'service__category')
    search_fields = ('provider__provider_name', 'service__name')


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = ('title', 'customer', 'service', 'city', 'urgency', 'status', 'created_at')
    list_filter = ('status', 'urgency', 'city')
    search_fields = ('title', 'customer__user__username')


@admin.register(ProviderMatch)
class ProviderMatchAdmin(admin.ModelAdmin):
    list_display = ('service_request', 'provider', 'match_score', 'status')
    list_filter = ('status',)