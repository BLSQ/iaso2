# Generated by Django 3.2.13 on 2022-07-14 14:17

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("iaso", "0155_alter_instance_validation_status"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="instancelocktable",
            name="deleted_at",
        ),
    ]
