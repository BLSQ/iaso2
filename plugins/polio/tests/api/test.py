import datetime
from iaso import models as m
from plugins.polio import models as pm


class PolioTestCaseMixin:
    @staticmethod
    def create_campaign(
        obr_name,
        account,
        source_version,
        country_ou_type,  # Should have the property category="COUNTRY"
        district_ou_type,
        country_name="Groland",
        district_name="Groville",
        vaccine=pm.VACCINES[0][0],
    ):
        country = m.OrgUnit.objects.create(
            org_unit_type=country_ou_type,
            version=source_version,
            name=country_name,
            validation_status=m.OrgUnit.VALIDATION_VALID,
            source_ref="PvtAI4RUMkr",
        )
        district = m.OrgUnit.objects.create(
            org_unit_type=district_ou_type,
            version=source_version,
            name=district_name,
            validation_status=m.OrgUnit.VALIDATION_VALID,
            source_ref="PvtAI4Rr",
        )
        campaign = pm.Campaign.objects.create(
            obr_name=obr_name,
            initial_org_unit=country,
            country=country,
            account=account,
            separate_scopes_per_round=False,
        )
        scope_group = m.Group.objects.create(name="campaign_scope", source_version=source_version)
        scope_group.org_units.set([district])  # FIXME: we should actually have children org units
        pm.CampaignScope.objects.create(campaign=campaign, vaccine=vaccine, group=scope_group)

        round_1 = pm.Round.objects.create(
            campaign=campaign,
            started_at=datetime.date(2021, 1, 1),
            ended_at=datetime.date(2021, 1, 10),
            number=1,
        )

        round_2 = pm.Round.objects.create(
            campaign=campaign,
            started_at=datetime.date(2021, 2, 1),
            ended_at=datetime.date(2021, 2, 10),
            number=2,
        )

        round_3 = pm.Round.objects.create(
            campaign=campaign,
            started_at=datetime.date(2021, 3, 1),
            ended_at=datetime.date(2021, 3, 10),
            number=3,
        )

        return [campaign, round_1, round_2, round_3, country, district]

    @staticmethod
    def add_scope_to_round(rnd, org_units, vaccine, source_version):
        group = m.Group.objects.create(
            name=f"{rnd.campaign.obr_name}_rnd_{rnd.number}_{vaccine}_round_scope", source_version=source_version
        )
        group.org_units.set(org_units)
        scope = pm.RoundScope.objects.create(round=rnd, vaccine=vaccine, group=group)
        return scope, group

    @staticmethod
    def replace_campaign_scope(campaign, org_units, vaccine, source_version):
        old_scopes = pm.CampaignScope.objects.filter(campaign=campaign)
        if old_scopes:
            old_scopes.delete()
        group = m.Group.objects.create(name=f"{campaign.obr_name}_scope", source_version=source_version)
        group.org_units.set(org_units)
        new_scope = pm.CampaignScope.objects.create(campaign=campaign, vaccine=vaccine, group=group)
        return new_scope

    @staticmethod
    def add_campaign_scope(campaign, org_units, vaccine, source_version):
        group = m.Group.objects.create(name=f"{campaign.obr_name}_scope", source_version=source_version)
        group.org_units.set(org_units)
        scope = pm.CampaignScope.objects.create(campaign=campaign, vaccine=vaccine, group=group)
        return scope

    @staticmethod
    def create_sub_activity(
        rnd,
        name,
        start_date,
        end_date,
        lqas_start_date=None,
        lqas_end_date=None,
        im_start_date=None,
        im_end_date=None,
    ):
        sub_activity = pm.SubActivity.objects.create(
            round=rnd,
            start_date=start_date,
            end_date=end_date,
            lqas_started_at=lqas_start_date,
            lqas_ended_at=lqas_end_date,
            im_started_at=im_start_date,
            im_ended_at=im_end_date,
            name=name,
        )
        return sub_activity

    @staticmethod
    def add_sub_activity_scope(sub_activity, org_units, vaccine, source_version):
        group = m.Group.objects.create(
            name=f"{sub_activity.round.campaign.obr_name}_{sub_activity.round.number}_{sub_activity.pk}_scope",
            source_version=source_version,
        )
        group.org_units.set(org_units)
        scope = pm.SubActivityScope.objects.create(subactivity=sub_activity, vaccine=vaccine, group=group)
        return scope
