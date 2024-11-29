# Generated by Django 4.2.16 on 2024-11-29 09:51

from django.db import migrations


def delete_unused_scopes(apps, schema_editor):
    Round = apps.get_model("polio", "Round")
    Campaign = apps.get_model("polio", "Campaign")
    CampaignScope = apps.get_model("polio", "CampaignScope")
    RoundScope = apps.get_model("polio", "RoundScope")

    round_scopes = RoundScope.objects.all().prefetch_related("round", "round__campaign")
    campaign_scopes = CampaignScope.objects.all().prefetch_related("campaign")

    campaign_scopes_ids = []
    round_scopes_ids = []

    for scope in campaign_scopes:
        if scope.campaign.separate_scopes_per_round:
            campaign_scopes_ids.append(scope.id)
    for scope in round_scopes:
        # Rounds without campaigns should be deleted in separate migration
        if not scope.round.campaign:
            continue
        if not scope.round.campaign.separate_scopes_per_round:
            round_scopes_ids.append(scope.id)

    CampaignScope.objects.filter(id__in=campaign_scopes_ids).delete()
    RoundScope.objects.filter(id__in=round_scopes_ids).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("polio", "0205_remove_campaign_budget_requested_at_wfeditable_old_and_more"),
    ]

    operations = [migrations.RunPython(delete_unused_scopes, migrations.RunPython.noop)]
