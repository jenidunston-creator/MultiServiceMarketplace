"""Small helper for Stripe, in TEST MODE only (keys that start with sk_test_).

Stripe supports New Zealand and NZD. The customer pays on Stripe's own hosted page, so card
details never touch this website. We talk to Stripe with the `requests` library.
"""
import requests
from django.conf import settings


def is_configured():
    """True only when a TEST secret key is set. Live keys (sk_live_) are refused on purpose."""
    return settings.STRIPE_SECRET_KEY.startswith('sk_test_')


def to_cents(amount_nzd):
    return int((amount_nzd * 100).quantize(1))


def create_checkout_session(amount_nzd, description, success_url, cancel_url, metadata, customer_email=''):
    data = {
        'mode': 'payment',
        'success_url': success_url,
        'cancel_url': cancel_url,
        'line_items[0][quantity]': 1,
        'line_items[0][price_data][currency]': 'nzd',
        'line_items[0][price_data][unit_amount]': to_cents(amount_nzd),
        'line_items[0][price_data][product_data][name]': description[:120],
    }
    if customer_email:
        data['customer_email'] = customer_email
    for key, value in metadata.items():
        data[f'metadata[{key}]'] = value
    response = requests.post(f'{settings.STRIPE_API_URL}/checkout/sessions',
                             auth=(settings.STRIPE_SECRET_KEY, ''), data=data, timeout=15)
    response.raise_for_status()
    return response.json()


def retrieve_session(session_id):
    response = requests.get(f'{settings.STRIPE_API_URL}/checkout/sessions/{session_id}',
                            auth=(settings.STRIPE_SECRET_KEY, ''), timeout=15)
    response.raise_for_status()
    return response.json()
