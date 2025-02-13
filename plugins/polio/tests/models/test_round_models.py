import datetime

from django.utils import timezone

from iaso import models as m
from iaso.test import APITestCase

from plugins.polio import models as pm
from plugins.polio.tests.api.test import PolioTestCaseMixin


class RoundModelTestCase(APITestCase, PolioTestCaseMixin):
    """
    Test Vaccine stock history API (viewset, filters, serializer).
    """

    @classmethod
    def setUpTestData(cls):
        # Datasource, source version, project and account
        cls.account, cls.datasource, cls.source_version, cls.project = cls.create_account_datasource_version_project(
            "Default source", "Default account", "Default project"
        )
        # anonymous user and user without needed permissions
        cls.user, cls.anon, cls.user_no_perms = cls.create_base_users(cls.account, ["iaso_polio"])
        # org unit types to create campaigns and scopes
        cls.ou_type_country = cls.create_org_unit_type(name="COUNTRY", projects=[cls.project])
        cls.ou_type_district = cls.create_org_unit_type(name="DISTRICT", projects=[cls.project])
        cls.obr_name = "DRC-DS-XXXX-TEST"
        # campaign
        cls.campaign, cls.rnd1, cls.rnd2, cls.rnd3, cls.country, cls.district = cls.create_campaign(
            cls.obr_name,
            cls.account,
            cls.source_version,
            cls.ou_type_country,
            cls.ou_type_district,
            "GROLAND",
            "GROVILLE",
        )
        # Switch to round scopes
        cls.campaign.separate_scopes_per_round = True
        cls.campaign.save()

        # Add round scopes
        cls.rnd1_scope_group = m.Group.objects.create(name="rnd1_scope", source_version=cls.source_version)
        cls.rnd1_scope_group.org_units.set([cls.district])
        cls.rnd1_scope = pm.RoundScope.objects.create(
            round=cls.rnd1, vaccine=pm.VACCINES[0][0], group=cls.rnd1_scope_group
        )
        cls.rnd2_scope_group = m.Group.objects.create(name="rnd2_scope", source_version=cls.source_version)
        cls.rnd2_scope_group.org_units.set([cls.district])
        cls.rnd2_scope = pm.RoundScope.objects.create(
            round=cls.rnd2, vaccine=pm.VACCINES[1][0], group=cls.rnd2_scope_group
        )
        cls.rnd3_scope_group = m.Group.objects.create(name="rnd3_scope", source_version=cls.source_version)
        cls.rnd3_scope_group.org_units.set([cls.district])
        cls.rnd3_scope = pm.RoundScope.objects.create(
            round=cls.rnd3, vaccine=pm.VACCINES[2][0], group=cls.rnd3_scope_group
        )

    def test_deleting_round_deletes_scope_and_group(self):
        self.assertEqual(
            m.Group.objects.count(), 4
        )  # One was created at the campaign level, hence 3 groups for rounds scopes + 1 for campaign scope
        self.assertEqual(pm.RoundScope.objects.count(), 3)

        self.rnd3.delete()

        self.assertEqual(pm.RoundScope.objects.count(), 2)
        self.assertEqual(m.Group.objects.count(), 3)

    def test_add_chronogram(self):
        now = timezone.now()

        polio_type = pm.CampaignType.objects.get(name=pm.CampaignType.POLIO)
        self.campaign.campaign_types.add(polio_type)

        date_in_past = (now - datetime.timedelta(days=1)).date()
        round_1 = pm.Round.objects.create(number=1, campaign=self.campaign, started_at=date_in_past)
        round_1.add_chronogram()
        self.assertEqual(
            round_1.chronograms.valid().count(), 0, "No chronogram should be created when `started_at` in the past."
        )

        round_2 = pm.Round.objects.create(number=2, campaign=self.campaign, started_at=now.date())
        round_2.add_chronogram()
        self.assertEqual(
            round_2.chronograms.valid().count(), 1, "A new chronogram should be created when `started_at` >= now."
        )

        round_3 = pm.Round.objects.create(number=3, campaign=self.campaign, started_at=now)
        round_3.add_chronogram()
        self.assertEqual(
            round_3.chronograms.valid().count(),
            1,
            "A new chronogram should be created even when `started_at` is a datetime object.",
        )

        self.campaign.campaign_types.remove(polio_type)
        measles_type = pm.CampaignType.objects.get(name=pm.CampaignType.MEASLES)
        self.campaign.campaign_types.add(measles_type)
        round_4 = pm.Round.objects.create(number=1, campaign=self.campaign, started_at=now.date())
        self.assertEqual(
            round_4.chronograms.valid().count(), 0, "No chronogram should be created for non-Polio campaigns."
        )
