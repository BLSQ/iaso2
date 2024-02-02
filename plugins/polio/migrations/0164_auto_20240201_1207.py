# Generated by Django 3.2.22 on 2024-02-01 12:07

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("polio", "0163_auto_20240123_1435"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="destructionreport",
            name="lot_number",
        ),
        migrations.AddField(
            model_name="destructionreport",
            name="lot_numbers",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(blank=True, max_length=200), default=list, size=None
            ),
        ),
    ]
