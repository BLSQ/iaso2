# Generated by Django 4.2.17 on 2024-12-23 16:18

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("polio", "0213_alter_vaccinerequestform_vaccine_type"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="rounddatehistoryentry",
            name="reason",
        ),
    ]
