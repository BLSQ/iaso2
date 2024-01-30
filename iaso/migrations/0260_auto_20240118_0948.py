# Generated by Django 4.2.9 on 2024-01-18 09:48

from django.db import migrations, IntegrityError, transaction


def create_feature_flags(apps, schema_editor):
    FeatureFlag = apps.get_model("iaso", "FeatureFlag")
    try:
        with transaction.atomic():
            FeatureFlag.objects.create(
                code="MOBILE_ORG_UNIT_REGISTRY",
                name="Mobile: Change requests.",
            )
    except IntegrityError:
        pass
    try:
        with transaction.atomic():
            FeatureFlag.objects.create(
                code="MOBILE_ENTITY_LIMITED_SEARCH",
                name="Mobile: Limit entities search.",
            )
    except IntegrityError:
        pass


def destroy_feature_flags(apps, schema_editor):
    FeatureFlag = apps.get_model("iaso", "FeatureFlag")
    FeatureFlag.objects.filter(code="MOBILE_ORG_UNIT_REGISTRY").delete()
    FeatureFlag.objects.filter(code="MOBILE_ENTITY_LIMITED_SEARCH").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("iaso", "0259_alter_orgunitchangerequest_created_at_and_more"),
    ]

    operations = [migrations.RunPython(create_feature_flags, destroy_feature_flags)]
