from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("fleet", "0004_servicerecord")]

    operations = [
        migrations.AlterField(
            model_name="fleet",
            name="owner",
            field=models.OneToOneField(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="owned_fleet", to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
