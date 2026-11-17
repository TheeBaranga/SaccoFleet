from django.db import migrations, models
import django.db.models.deletion


def assign_existing_accounts(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    Fleet = apps.get_model("fleet", "Fleet")
    db = schema_editor.connection.alias
    existing_fleets = dict(Fleet.objects.using(db).exclude(owner=None).values_list("owner_id", "pk"))
    for pk in User.objects.using(db).values_list("pk", flat=True).iterator():
        fleet_id = existing_fleets.get(pk)
        if fleet_id is None:
            fleet_id = Fleet.objects.using(db).create(owner_id=pk).pk
        User.objects.using(db).filter(pk=pk).update(sacco_id=fleet_id)


class Migration(migrations.Migration):
    dependencies = [("accounts", "0002_loginbucket"), ("fleet", "0005_optional_legacy_owner")]

    operations = [
        migrations.AddField(
            model_name="user", name="sacco",
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.PROTECT, related_name="members", to="fleet.fleet",
            ),
        ),
        migrations.AddField(
            model_name="user", name="role",
            field=models.CharField(
                choices=[("manager", "Manager"), ("operations", "Operations staff")],
                default="manager", max_length=12,
            ),
        ),
        migrations.RunPython(assign_existing_accounts),
        migrations.AlterField(
            model_name="user", name="sacco",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT, related_name="members", to="fleet.fleet",
            ),
        ),
        migrations.AddConstraint(
            model_name="user",
            constraint=models.CheckConstraint(
                condition=models.Q(role="manager") | models.Q(role="operations", is_staff=False, is_superuser=False),
                name="accounts_valid_sacco_role",
            ),
        ),
    ]
