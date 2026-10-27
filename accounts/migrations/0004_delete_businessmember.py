from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_businessmember_by_name'),
    ]

    operations = [
        migrations.DeleteModel(
            name='BusinessMember',
        ),
    ]
