import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def copy_names(apps, schema_editor):
    """Existing team members linked to an account get their name copied across."""
    BusinessMember = apps.get_model('accounts', 'BusinessMember')
    for member in BusinessMember.objects.select_related('user'):
        if member.user_id and not member.full_name:
            name = f'{member.user.first_name} {member.user.last_name}'.strip()
            member.full_name = name or member.user.username
            member.save(update_fields=['full_name'])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_alter_user_role'),
    ]

    operations = [
        migrations.AddField(
            model_name='businessmember',
            name='full_name',
            field=models.CharField(default='', max_length=120),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='businessmember',
            name='email',
            field=models.EmailField(blank=True, max_length=254),
        ),
        migrations.AddField(
            model_name='businessmember',
            name='phone',
            field=models.CharField(blank=True, max_length=30),
        ),
        migrations.AlterField(
            model_name='businessmember',
            name='position',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AlterField(
            model_name='businessmember',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    related_name='business_memberships', to=settings.AUTH_USER_MODEL),
        ),
        migrations.RunPython(copy_names, migrations.RunPython.noop),
    ]
