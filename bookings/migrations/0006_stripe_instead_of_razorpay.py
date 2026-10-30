from django.db import migrations, models


def to_stripe(apps, schema_editor):
    apps.get_model('bookings', 'Payment').objects.update(method='STRIPE')


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0005_convert_old_payments'),
    ]

    operations = [
        migrations.RenameField('paymenttransaction', 'razorpay_order_id', 'stripe_session_id'),
        migrations.RenameField('paymenttransaction', 'razorpay_payment_id', 'stripe_payment_id'),
        migrations.AlterField('paymenttransaction', 'stripe_session_id', models.CharField(max_length=120, unique=True)),
        migrations.AlterField('paymenttransaction', 'stripe_payment_id', models.CharField(blank=True, max_length=120)),
        migrations.AlterField('payment', 'method', models.CharField(
            choices=[('STRIPE', 'Stripe (test mode)')], default='STRIPE', max_length=10)),
        migrations.RunPython(to_stripe, migrations.RunPython.noop),
    ]
