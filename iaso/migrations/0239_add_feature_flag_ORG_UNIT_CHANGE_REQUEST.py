# Generated by Django 3.2.22 on 2023-10-25 09:36

from django.db import migrations


def create_feature_flags(apps, schema_editor):
    FeatureFlag = apps.get_model("iaso", "FeatureFlag")
    FeatureFlag.objects.create(
        code="ORG_UNIT_CHANGE_REQUEST",
        name="Request changes to org units.",
    )


def destroy_feature_flags(apps, schema_editor):
    FeatureFlag = apps.get_model("iaso", "FeatureFlag")
    FeatureFlag.objects.filter(code="ORG_UNIT_CHANGE_REQUEST").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("iaso", "0238_rename_new_accuracy_orgunitchangerequest_new_location_accuracy_uuid"),
    ]

    operations = [migrations.RunPython(create_feature_flags, destroy_feature_flags)]
