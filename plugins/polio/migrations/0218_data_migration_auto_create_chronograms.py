# Generated by Django 4.2.18 on 2025-02-04 09:17

from django.db import migrations

from django.utils.timezone import now


def migrate_data_forward(apps, schema_editor):
    Chronogram = apps.get_model("polio", "Chronogram")
    ChronogramTask = apps.get_model("polio", "ChronogramTask")
    ChronogramTemplateTask = apps.get_model("polio", "ChronogramTemplateTask")
    Round = apps.get_model("polio", "Round")

    rounds = (
        Round.objects.filter(
            campaign__campaign_types__name="Polio",
            started_at__gte=now(),
            campaign__deleted_at__isnull=True,  # The campaign has not been soft-deleted.
        )
        .select_related("campaign__account")
        .prefetch_related("campaign__campaign_types", "chronograms")
    )

    for round in rounds:
        if round.chronograms.filter(deleted_at__isnull=True).exists():
            continue

        chronogram_template_tasks = ChronogramTemplateTask.objects.filter(
            deleted_at__isnull=True, account=round.campaign.account
        )
        if not chronogram_template_tasks.exists():
            continue

        chronogram = Chronogram.objects.create(round=round, created_by=None)

        tasks = [
            ChronogramTask(
                chronogram=chronogram,
                created_by=None,
                description_en=template.description_en,
                description_fr=template.description_fr,
                period=template.period,
                start_offset_in_days=template.start_offset_in_days,
            )
            for template in chronogram_template_tasks
        ]
        ChronogramTask.objects.bulk_create(tasks)


class Migration(migrations.Migration):
    dependencies = [
        ("polio", "0217_round_is_test"),
    ]

    operations = [migrations.RunPython(migrate_data_forward, migrations.RunPython.noop, elidable=True)]
