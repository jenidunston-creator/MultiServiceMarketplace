"""One small helper to create a notification for a user."""
from accounts.models import User
from .models import Notification


def notify(user, kind, title, message, link=''):
    if user is None:
        return None
    return Notification.objects.create(
        user=user, notification_type=kind, title=title, message=message, link=link)


def notify_admins(kind, title, message, link=''):
    for admin in User.objects.filter(is_active=True, role=User.Role.ADMIN):
        notify(admin, kind, title, message, link)
