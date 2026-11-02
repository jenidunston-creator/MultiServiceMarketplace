"""Forgot password. The reset link is only ever sent by email, never shown on the page,
because anyone could type someone else's email address."""
from django import forms
from django.conf import settings
from django.contrib.auth import views as auth_views
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from . import security
from .models import User


class ForgotForm(forms.Form):
    email = forms.EmailField(max_length=254)


def can_self_reset(user):
    """Admin accounts are not reset by email. An admin uses `python manage.py changepassword`."""
    return user.is_active and not user.is_superuser and user.role != User.Role.ADMIN


def password_forgot(request):
    form = ForgotForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['email'].strip().lower()
        slowed = (security.too_many(f'forgot-ip:{security.client_ip(request)}', 10, 3600)
                  or security.too_many(f'forgot-email:{email}', 3, 3600))
        if not slowed:
            for user in User.objects.filter(email__iexact=email):
                if not can_self_reset(user):
                    continue
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                link = request.build_absolute_uri(
                    reverse('password_reset_confirm', args=[uid, default_token_generator.make_token(user)]))
                send_mail('Reset your Servana password',
                          f'Hi {user.first_name or user.username},\n\n'
                          f'Open this link to choose a new password. It works once, for 1 hour:\n{link}\n\n'
                          'If you did not ask for this, ignore this email. Your password has not changed.\n',
                          settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True)
        # the same answer every time, so nobody can find out which emails have an account
        return redirect('password_forgot_done')
    return render(request, 'accounts/password_forgot.html', {'form': form})


class ResetConfirmView(auth_views.PasswordResetConfirmView):
    """Django's own safe reset page (one-time token, kept out of the address bar), plus our rules."""
    template_name = 'accounts/password_reset_confirm.html'
    success_url = reverse_lazy('password_reset_complete')

    def get_user(self, uidb64):
        user = super().get_user(uidb64)
        return user if user is not None and can_self_reset(user) else None

    def form_valid(self, form):
        response = super().form_valid(form)
        security.reset(f'login-user:{self.user.username.strip().lower()}')     # lift a failed-login lock
        return response
