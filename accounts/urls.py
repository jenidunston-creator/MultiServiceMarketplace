from django.contrib.auth import views as auth_views
from django.urls import path
from django.views.generic import TemplateView

from . import password_reset, verification, views
from .login import ThrottledLoginView

urlpatterns = [
    path(
        'login/',
        ThrottledLoginView.as_view(
            template_name='accounts/login.html',
            redirect_authenticated_user=True,
        ),
        name='login',
    ),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('signup/', views.signup_view, name='signup'),
    path('profile/', views.provider_profile_edit, name='provider_profile'),

    # forgot password
    path('forgot/', password_reset.password_forgot, name='password_forgot'),
    path('forgot/sent/', TemplateView.as_view(template_name='accounts/password_forgot_done.html'),
         name='password_forgot_done'),
    path('reset/<uidb64>/<token>/', password_reset.ResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', TemplateView.as_view(template_name='accounts/password_reset_complete.html'),
         name='password_reset_complete'),

    # verification: email, mobile, passport and visa
    path('verify/', verification.verify_center, name='verify_center'),
    path('verify/email/send/', verification.verify_email_send, name='verify_email_send'),
    path('verify/email/<str:token>/', verification.verify_email_confirm, name='verify_email_confirm'),
    path('verify/phone/send/', verification.verify_phone_send, name='verify_phone_send'),
    path('verify/phone/confirm/', verification.verify_phone_confirm, name='verify_phone_confirm'),
    path('verify/id/', verification.verify_identity, name='verify_identity'),
    path('verify/document/<int:pk>/<str:which>/', verification.identity_document, name='identity_document'),
]