from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

from accounts import views as account_views
from communication import views as communication_views

urlpatterns = [
    path('admin/', admin.site.urls),

    # home page
    path('', TemplateView.as_view(template_name='home.html'), name='home'),

    # apps
    path('accounts/', include('accounts.urls')),
    path('services/', include('services.urls')),
    path('bookings/', include('bookings.urls')),
    path('quotations/', include('bookings.quotation_urls')),
    path('communication/', include('communication.urls')),
    # same page, second address (your menu link uses /chat/notifications/)
    path('chat/notifications/', communication_views.notifications),
    path('chat/', communication_views.chat),

    # dashboards (one for each role)
    path('dashboard/', account_views.dashboard_redirect, name='dashboard'),
    path('dashboard/customer/', account_views.customer_dashboard, name='customer_dashboard'),
    path('dashboard/provider/', account_views.provider_dashboard, name='provider_dashboard'),
    path('dashboard/business/', account_views.business_dashboard, name='business_dashboard'),
    path('dashboard/admin-panel/', account_views.admin_dashboard, name='admin_dashboard'),

    # admin actions
    path('dashboard/admin-panel/users/<int:pk>/toggle/', account_views.admin_user_toggle, name='admin_user_toggle'),
    path('dashboard/admin-panel/providers/<int:pk>/verify/', account_views.admin_provider_verify, name='admin_provider_verify'),
    path('dashboard/admin-panel/reviews/<int:pk>/toggle/', account_views.admin_review_toggle, name='admin_review_toggle'),
    path('dashboard/admin-panel/bookings.csv', account_views.admin_bookings_csv, name='admin_bookings_csv'),

]

# show uploaded images while DEBUG = True
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
