# Generated by Django 3.1.14 on 2022-01-24 17:35

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ("iaso", "0116_auto_20220124_1342"),
    ]

    operations = [
        migrations.AlterField(
            model_name="entity",
            name="attributes",
            field=models.OneToOneField(
                blank=True,
                help_text="instance",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="iaso.instance",
            ),
        ),
        migrations.AlterField(
            model_name="entity",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4, editable=False),
        ),
    ]
