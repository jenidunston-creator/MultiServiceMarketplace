from django.db import migrations


def trust_existing(apps, schema_editor):
    """People who signed up before the checks existed keep working.
    Only accounts created from now on must pass email, mobile and passport/visa checks."""
    User = apps.get_model('accounts', 'User')
    User.objects.update(email_verified=True, phone_verified=True, id_verified=True)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_verification'),
    ]

    operations = [
        migrations.RunPython(trust_existing, migrations.RunPython.noop),
    ]
