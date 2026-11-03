from django.conf import settings


def site_details(request):
    """Makes the contact details, social links and the notification bell data available in every template."""
    data = {'SITE_CONTACT': settings.SITE_CONTACT, 'SOCIAL_LINKS': settings.SOCIAL_LINKS,
            'unread_count': 0, 'latest_notifications': []}
    user = getattr(request, 'user', None)
    if user is not None and user.is_authenticated:
        from communication.models import Notification
        mine = Notification.objects.filter(user=user)
        data['unread_count'] = mine.filter(is_read=False).count()
        data['latest_notifications'] = list(mine[:5])
    return data
