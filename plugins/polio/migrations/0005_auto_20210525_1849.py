# Generated by Django 3.0.14 on 2021-05-25 18:49

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("polio", "0004_auto_20210505_1813"),
    ]

    operations = [
        migrations.AddField(
            model_name="campaign",
            name="preperadness_spreadsheet_url",
            field=models.URLField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="Preparedness",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("spreadsheet_url", models.URLField()),
                ("national_score", models.DecimalField(decimal_places=2, max_digits=10, verbose_name="National Score")),
                ("regional_score", models.DecimalField(decimal_places=2, max_digits=10, verbose_name="Regional Score")),
                ("district_score", models.DecimalField(decimal_places=2, max_digits=10, verbose_name="District Score")),
                ("payload", django.contrib.postgres.fields.jsonb.JSONField()),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("campaign", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="polio.Campaign")),
            ],
        ),
    ]
