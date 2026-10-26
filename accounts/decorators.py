from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def role_required(*allowed_roles):
    """Only logged-in users with one of the allowed roles can open the page."""

    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user = request.user
            role = 'ADMIN' if user.is_superuser else user.role
            if role in allowed_roles:
                return view_func(request, *args, **kwargs)
            raise PermissionDenied  # shows a 403 Forbidden page

        return wrapper

    return decorator