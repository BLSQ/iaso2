"""Add the polio permission for existing user in account polio"""

from django.db import migrations


def add_user_permissions(apps, schema_editor):
    Account = apps.get_model("iaso", "Account")
    Permission = apps.get_model("auth", "Permission")
    permissions = Permission.objects.filter(
        codename__in=[
            "iaso_polio",
        ]
    )
    try:
        account = Account.objects.get(name="polio")
    except:
        print("No polio account")
        return
    for profile in account.profile_set.all():
        user = profile.user
        print(f"Adding perms {permissions} to {profile}")
        user.user_permissions.add(*permissions)


class Migration(migrations.Migration):
    dependencies = [
        ("menupermissions", "0021_auto_20210901_1228"),
    ]

    operations = [migrations.RunPython(add_user_permissions, migrations.RunPython.noop)]
