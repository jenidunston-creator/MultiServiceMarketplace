import uuid

from django.db import migrations


def backfill(apps, schema_editor):
    """Payments already released before payouts existed get a payout record too."""
    Payment = apps.get_model('bookings', 'Payment')
    Payout = apps.get_model('bookings', 'Payout')
    for p in Payment.objects.filter(status='RELEASED').select_related('booking'):
        Payout.objects.get_or_create(
            payment=p, defaults={'provider_id': p.booking.provider_id, 'amount': p.amount_paid,
                                 'reference': 'PAYOUT-' + uuid.uuid4().hex[:10].upper()})


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0007_payout'),
    ]

    operations = [
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
