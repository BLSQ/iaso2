# Generated by Django 4.2.16 on 2024-10-23 17:03

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("polio", "0198_remove_po_prefix"),
    ]

    operations = [
        migrations.AddField(
            model_name="destructionreport",
            name="comment",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="outgoingstockmovement",
            name="comment",
            field=models.TextField(blank=True, null=True),
        ),
    ]
