import re

from django.contrib import messages
from django.shortcuts import redirect

# Unverified people can look around, but they cannot book, pay, offer services or use chat.
BLOCKED_PATHS = re.compile(
    r'^/(bookings/|quotations/|communication/|chat/(?!notifications)|services/new/|services/\d+/(edit|delete)/)')


class VerificationRequiredMiddleware:
    """Stops accounts that are not fully verified from using the protected parts of the site."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if user.is_authenticated and not user.is_verified:
            path = request.path
            is_account_page = path.startswith(('/accounts/', '/admin/', '/static/', '/media/'))
            blocked = bool(BLOCKED_PATHS.match(path)) or (request.method == 'POST' and not is_account_page)
            if blocked:
                messages.warning(request, 'Please finish verifying your account first. '
                                          'You need a verified email, mobile number and passport/visa.')
                return redirect('verify_center')
        return self.get_response(request)
