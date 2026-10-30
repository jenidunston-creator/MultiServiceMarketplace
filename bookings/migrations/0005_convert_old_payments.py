from django.db import migrations
from django.db.models import F


def convert(apps, schema_editor):
    """Old payments (card, bank, cash) become the new held-money system."""
    Payment = apps.get_model('bookings', 'Payment')
    Payment.objects.filter(status='PAID').update(status='HELD', amount_paid=F('amount'))
    Payment.objects.filter(status='AWAITING').update(status='PENDING')
    Payment.objects.filter(status='REJECTED').update(status='FAILED')
    Payment.objects.update(method='CARD')


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0004_escrow_payments'),
    ]

    operations = [
        migrations.RunPython(convert, migrations.RunPython.noop),
    ]
