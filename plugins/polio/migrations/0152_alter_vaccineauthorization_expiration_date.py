# Generated by Django 3.2.22 on 2023-11-07 18:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('polio', '0151_alter_rounddatehistoryentry_reason'),
    ]

    operations = [
        migrations.AlterField(
            model_name='vaccineauthorization',
            name='expiration_date',
            field=models.DateField(blank=True, null=True),
        ),
    ]
