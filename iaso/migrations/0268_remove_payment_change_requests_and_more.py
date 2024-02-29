# Generated by Django 4.2.10 on 2024-02-29 13:47

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("iaso", "0267_paymentlot_status_alter_payment_status"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="payment",
            name="change_requests",
        ),
        migrations.RemoveField(
            model_name="potentialpayment",
            name="change_requests",
        ),
        migrations.AddField(
            model_name="orgunitchangerequest",
            name="payment",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="change_requests",
                to="iaso.payment",
            ),
        ),
        migrations.AddField(
            model_name="orgunitchangerequest",
            name="potential_payment",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="change_requests",
                to="iaso.paymentlot",
            ),
        ),
    ]
