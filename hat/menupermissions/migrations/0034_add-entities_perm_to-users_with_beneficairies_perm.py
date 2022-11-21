# Generated by Django 3.1.14 on 2022-03-25 14:37
from django.contrib.auth.management import create_permissions
from django.db import migrations


class Migration(migrations.Migration):
    def add_user_permissions(apps, schema_editor):
        # Ensure the permissions are created in the databse
        # cf https://stackoverflow.com/questions/38822273/how-to-add-a-permission-to-a-user-group-during-a-django-migration/41564061#41564061
        for app_config in apps.get_app_configs():
            app_config.models_module = True
            create_permissions(app_config, verbosity=0)
            app_config.models_module = None

        Permission = apps.get_model("auth", "Permission")
        new_permission = Permission.objects.get(codename="iaso_entities")

        User = apps.get_model("auth", "User")

        users = User.objects.filter(user_permissions=Permission.objects.get(codename="iaso_beneficiaries"))

        for user in users:
            print(f"Adding perms {new_permission} to {user}")
            user.user_permissions.add(new_permission)

    dependencies = [
        ("menupermissions", "0033_alter_custompermissionsupport_options"),
    ]

    operations = [
        # We don't need this permission anymore, just remove the code
        # migrations.RunPython(add_user_permissions, migrations.RunPython.noop),
    ]
