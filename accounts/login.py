from django.contrib import messages
from django.contrib.auth import views as auth_views

from . import security

MAX_FAILS = 5          # wrong passwords allowed for one username
MAX_FAILS_IP = 25      # and for one computer (a classroom shares one address)
LOCK_SECONDS = 15 * 60  # then the login is locked for 15 minutes


class ThrottledLoginView(auth_views.LoginView):
    """The normal login page, but guessing passwords is slowed down."""

    def _keys(self, request):
        username = (request.POST.get('username') or '').strip().lower()
        return [(f'login-ip:{security.client_ip(request)}', MAX_FAILS_IP), (f'login-user:{username}', MAX_FAILS)]

    def post(self, request, *args, **kwargs):
        if any(security.is_blocked(key, limit) for key, limit in self._keys(request)):
            messages.error(request, 'Too many failed logins. Please wait 15 minutes and try again.')
            return self.get(request, *args, **kwargs)
        return super().post(request, *args, **kwargs)

    def form_invalid(self, form):
        for key, limit in self._keys(self.request):
            security.too_many(key, limit, LOCK_SECONDS)
        return super().form_invalid(form)

    def form_valid(self, form):
        for key, limit in self._keys(self.request):
            if key.startswith('login-user:'):
                security.reset(key)
        return super().form_valid(form)
