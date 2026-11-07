from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_alter_user_phone_number'),
    ]

    operations = [
        migrations.AddField(
            model_name='passwordresetotp',
            name='attempts',
            field=models.PositiveSmallIntegerField(default=0),
        ),
    ]
