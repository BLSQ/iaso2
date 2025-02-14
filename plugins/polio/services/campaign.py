from plugins.polio.models import Campaign, Round


def delete_old_scopes_after_scope_level_switch(switch_to_campaign: bool, switch_to_round: bool, campaign: Campaign):
    """
    Deletes campaign-level scopes when switching to round-level, or deletes round-level scopes when switching to campaign-level.
    All subactivity scopes are also deleted when any switch is done.
    """
    if switch_to_campaign:
        for round in campaign.rounds.all():
            if round.scopes.exists():
                round.scopes.all().delete()
            _delete_sub_activity_scopes_from_round(round)
    elif switch_to_round:
        if campaign.scopes.exists():
            campaign.scopes.all().delete()
        for round in campaign.rounds.all():
            _delete_sub_activity_scopes_from_round(round)


def _delete_sub_activity_scopes_from_round(round: Round):
    for sub_activity in round.sub_activities.all():
        if sub_activity.scopes.exists():
            sub_activity.scopes.all().delete()
