# Generated by Django 4.2.15 on 2024-09-03 14:30

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("iaso", "0295_merge_20240819_1249"),
    ]

    operations = [
        migrations.AddField(
            model_name="groupset",
            name="group_belonging",
            field=models.TextField(
                choices=[("SINGLE", "Single"), ("MULTIPLE", "Multiple")],
                default="SINGLE",
                max_length=10,
            ),
        ),
    ]
