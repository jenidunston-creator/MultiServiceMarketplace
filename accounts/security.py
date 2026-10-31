"""Small safety helpers: rate limits (stop guessing and spam) and a filter for scam text."""
import re

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone


# ---------------------------------------------------------------- who counts as "verified"
def verified_user_q(prefix=''):
    """Database filter for people who are fully verified: email, mobile and passport/visa approved,
    and the passport and visa still in date today. Admins always count.
    `prefix` is the path to the user, for example 'provider__user__'."""
    today = timezone.localdate()
    staff = Q(**{f'{prefix}is_superuser': True}) | Q(**{f'{prefix}role': 'ADMIN'})
    checked = Q(**{f'{prefix}email_verified': True, f'{prefix}phone_verified': True,
                   f'{prefix}id_verified': True})
    in_date = (~Q(**{f'{prefix}identity__passport_expiry__lte': today})
               & ~Q(**{f'{prefix}identity__visa_expiry__lte': today}))
    return staff | (checked & in_date)


# ---------------------------------------------------------------- rate limiting
def too_many(key, limit, seconds):
    """Count one attempt for `key`. Returns True when it went over `limit` within `seconds`."""
    cache_key = f'rate:{key}'
    count = cache.get(cache_key, 0) + 1
    cache.set(cache_key, count, seconds)
    return count > limit


def is_blocked(key, limit):
    return cache.get(f'rate:{key}', 0) >= limit


def reset(key):
    cache.delete(f'rate:{key}')


def client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    return (forwarded.split(',')[0].strip() if forwarded else request.META.get('REMOTE_ADDR', '')) or 'unknown'


# ---------------------------------------------------------------- scam text filter
URL_RE = re.compile(r'(https?://|www\.|\b[a-z0-9-]+\.(com|net|org|nz|co|io|me|ly|xyz|info)\b)', re.I)
EMAIL_RE = re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+')
PHONE_RE = re.compile(r'(\+?\d[\s().-]*){8,}')
SCAM_WORDS = ['western union', 'moneygram', 'gift card', 'giftcard', 'bitcoin', 'crypto', 'wire transfer',
              'bank transfer', 'pay me directly', 'pay outside', 'outside the site', 'whatsapp', 'telegram',
              'send me your password', 'otp code', 'cash only before']


def clean_public_text(value):
    """Used on text other people will read. Blocks links, emails, phone numbers and off-site payment talk,
    which is how most marketplace scams try to move people away from the protected payment."""
    text = value or ''
    lowered = text.lower()
    if URL_RE.search(text) or EMAIL_RE.search(text) or PHONE_RE.search(text):
        raise ValidationError(
            'For your safety, please do not put links, email addresses or phone numbers here. '
            'Servana keeps all contact and payments on the site.')
    for word in SCAM_WORDS:
        if word in lowered:
            raise ValidationError(
                'This text mentions paying or talking outside Servana, which is not allowed. '
                'All payments must go through the site.')
    return text
