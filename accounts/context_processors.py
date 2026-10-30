from django.conf import settings


def site_details(request):
    """Makes the contact details and social links available in every template."""
    return {'SITE_CONTACT': settings.SITE_CONTACT, 'SOCIAL_LINKS': settings.SOCIAL_LINKS}
