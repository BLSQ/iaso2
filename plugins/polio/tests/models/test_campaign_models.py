from iaso import models as m
from iaso.test import TestCase

from plugins.polio.models import VACCINES, Campaign, CampaignType, RoundScope
from plugins.polio.tests.api.test import PolioTestCaseMixin


class CampaignTestCase(TestCase, PolioTestCaseMixin):
    """
    Test Campaign model.
    """

    @classmethod
    def setUpTestData(cls):
        # vaccines
        cls.mopv2 = VACCINES[0][0]
        cls.nopv2 = VACCINES[1][0]
        cls.bopv = VACCINES[2][0]
        cls.nopv2_bopv = VACCINES[3][0]
        # User.
        cls.account, cls.data_source, cls.source_version, cls.project = cls.create_account_datasource_version_project(
            source_name="Data Source", account_name="Account", project_name="Project"
        )
        cls.user = cls.create_user_with_profile(
            email="john@polio.org",
            username="test",
            first_name="John",
            last_name="Doe",
            account=cls.account,
            permissions=["iaso_polio_budget"],
        )
        # Org unit types
        cls.org_unit_type_country = cls.create_org_unit_type(name="COUNTRY", projects=[cls.project])
        cls.org_unit_type_district = cls.create_org_unit_type(name="DISTRICT", projects=[cls.project])

        # Campaigns types.
        cls.polio_type = CampaignType.objects.get(name=CampaignType.POLIO)
        cls.measles_type = CampaignType.objects.get(name=CampaignType.MEASLES)

        # Polio Campaigns.
        # Campaign 1: separate_scopes_per_round=False, no subactivities
        (
            cls.polio_campaign,
            cls.polio_round_1,
            cls.polio_round_2,
            cls.polio_round_3,
            cls.country,
            cls.district,
        ) = cls.create_campaign(
            obr_name="Polio",
            account=cls.account,
            source_version=cls.source_version,
            country_ou_type=cls.org_unit_type_country,
            district_ou_type=cls.org_unit_type_district,
        )

        cls.polio_campaign.campaign_types.set([cls.polio_type])

        # Campaign 2: separate_scopes_per_rounds=True, no subactivities
        (
            cls.polio_campaign2,
            cls.polio2_round_1,
            cls.polio2_round_2,
            cls.polio2_round_3,
            cls.country2,
            cls.country2_district,
        ) = cls.create_campaign(
            obr_name="Polio2",
            account=cls.account,
            source_version=cls.source_version,
            country_ou_type=cls.org_unit_type_country,
            district_ou_type=cls.org_unit_type_district,
            country_name="COUNTRY2",
            district_name="COUNTRY2_DISTRICT1",
        )

        cls.polio_campaign2.campaign_types.set([cls.polio_type])

        # Switch campaign 2 to separate scopes per round to test model methods
        cls.polio_campaign2.separate_scopes_per_round = True
        cls.polio_campaign2.save()

        # Add districts to country 2, to be able to have different round scopes
        cls.country2_district2 = cls.create_valid_org_unit(
            type=cls.org_unit_type_district,
            version=cls.source_version,
            name="COUNTRY2_DISTRICT2",
        )
        cls.country2_district3 = cls.create_valid_org_unit(
            type=cls.org_unit_type_district,
            version=cls.source_version,
            name="COUNTRY2_DISTRICT3",
        )
        cls.country2_district4 = cls.create_valid_org_unit(
            type=cls.org_unit_type_district,
            version=cls.source_version,
            name="COUNTRY2_DISTRICT4",
        )
        cls.country2_district5 = cls.create_valid_org_unit(
            type=cls.org_unit_type_district,
            version=cls.source_version,
            name="COUNTRY2_DISTRICT5",
        )

        # Add round scopes to campaign 2
        cls.add_scope_to_round(
            rnd=cls.polio2_round_1,
            vaccine=cls.mopv2,
            org_units=[cls.country2_district],
            source_version=cls.source_version,
        )
        cls.add_scope_to_round(
            rnd=cls.polio2_round_2,
            vaccine=cls.nopv2_bopv,
            org_units=[cls.country2_district2, cls.country2_district3],
            source_version=cls.source_version,
        )

        # Campaign 3: separate_scopes_per_round=False, with subactivities
        (
            cls.polio_campaign3,
            cls.polio3_round_1,
            cls.polio3_round_2,
            cls.polio3_round_3,
            _,
            _,
        ) = cls.create_campaign(
            obr_name="Polio3",
            account=cls.account,
            source_version=cls.source_version,
            country_ou_type=cls.org_unit_type_country,
            district_ou_type=cls.org_unit_type_district,
        )
        cls.polio_campaign3.campaign_types.set([cls.polio_type])
        # Change country to country 2 so we can reuse the districts
        cls.polio_campaign3.initial_org_unit = cls.country2
        cls.polio_campaign3.save()

        # Replace default scope with larger scope, so we can have different scopes for subactivities
        cls.replace_campaign_scope(
            campaign=cls.polio_campaign3,
            org_units=[cls.country2_district, cls.country2_district2, cls.country2_district3],
            source_version=cls.source_version,
            vaccine=cls.mopv2,
        )

        # Add subactivities
        cls.polio3_round_1_sub_activity1 = cls.create_sub_activity(
            rnd=cls.polio3_round_1,
            name="rnd1_activity1",
            start_date=cls.polio3_round_1.started_at,
            end_date=cls.polio3_round_1.ended_at,
        )
        cls.add_sub_activity_scope(
            sub_activity=cls.polio3_round_1_sub_activity1,
            org_units=[cls.country2_district],
            vaccine=cls.nopv2_bopv,
            source_version=cls.source_version,
        )
        cls.polio3_round_2_sub_activity1 = cls.create_sub_activity(
            rnd=cls.polio3_round_2,
            name="rnd2_activity1",
            start_date=cls.polio3_round_2.started_at,
            end_date=cls.polio3_round_2.ended_at,
        )
        cls.add_sub_activity_scope(
            sub_activity=cls.polio3_round_2_sub_activity1,
            org_units=[cls.country2_district2],
            vaccine=cls.bopv,
            source_version=cls.source_version,
        )

        # Campaign 4: separate scopes per round and subactivities
        (
            cls.polio_campaign4,
            cls.polio4_round_1,
            cls.polio4_round_2,
            cls.polio4_round_3,
            _,
            _,
        ) = cls.create_campaign(
            obr_name="Polio4",
            account=cls.account,
            source_version=cls.source_version,
            country_ou_type=cls.org_unit_type_country,
            district_ou_type=cls.org_unit_type_district,
        )
        cls.polio_campaign4.campaign_types.set([cls.polio_type])
        # switch to round scopes
        cls.polio_campaign4.separate_scopes_per_round = True
        # Change country to country 2 so we can reuse the districts
        cls.polio_campaign4.initial_org_unit = cls.country2
        cls.polio_campaign4.save()

        # Add round scopes to campaign 4
        cls.add_scope_to_round(
            rnd=cls.polio4_round_1,
            vaccine=cls.mopv2,
            org_units=[cls.country2_district],
            source_version=cls.source_version,
        )
        cls.add_scope_to_round(
            rnd=cls.polio4_round_2,
            vaccine=cls.bopv,
            org_units=[cls.country2_district2, cls.country2_district3],
            source_version=cls.source_version,
        )

        # Add subactivities
        cls.polio4_round_1_sub_activity1 = cls.create_sub_activity(
            rnd=cls.polio4_round_1,
            name="rnd1_activity1",
            start_date=cls.polio4_round_1.started_at,
            end_date=cls.polio4_round_1.ended_at,
        )
        cls.add_sub_activity_scope(
            sub_activity=cls.polio4_round_1_sub_activity1,
            org_units=[cls.country2_district],
            vaccine=cls.nopv2_bopv,
            source_version=cls.source_version,
        )
        cls.polio4_round_2_sub_activity1 = cls.create_sub_activity(
            rnd=cls.polio4_round_2,
            name="rnd2_activity1",
            start_date=cls.polio4_round_2.started_at,
            end_date=cls.polio4_round_2.ended_at,
        )
        cls.add_sub_activity_scope(
            sub_activity=cls.polio4_round_2_sub_activity1,
            org_units=[cls.country2_district2],
            vaccine=cls.mopv2,
            source_version=cls.source_version,
        )

        # Non polio campaigns
        cls.measles_campaign = Campaign.objects.create(obr_name="Measles", account=cls.account)
        cls.measles_campaign.campaign_types.set([cls.measles_type])

    def test_polio_campaign_manager(self):
        self.assertEqual(Campaign.objects.count(), 5)
        self.assertEqual(Campaign.polio_objects.count(), 4)

        polio_campaign = Campaign.polio_objects.first()
        self.assertEqual(polio_campaign.campaign_types.first().name, CampaignType.POLIO)

    def test_has_polio_type(self):
        self.assertTrue(Campaign.polio_objects.first().has_polio_type)
        self.assertFalse(self.measles_campaign.has_polio_type)

    def test_vaccine_properties_with_separate_scopes_per_round(self):
        # strings
        self.assertEqual(self.polio_campaign2.vaccines, f"{self.mopv2}, {self.nopv2_bopv}")
        self.assertEqual(self.polio_campaign2.vaccines_extended, f"{self.mopv2}, {self.nopv2_bopv}")
        self.assertEqual(self.polio_campaign2.vaccines_full, f"{self.mopv2}, {self.nopv2_bopv}")
        self.assertEqual(self.polio_campaign2.single_vaccines_extended, f"{self.bopv}, {self.mopv2}, {self.nopv2}")
        # lists
        self.assertEqual(self.polio_campaign2.campaign_level_vaccines_list, [])
        self.assertEqual(self.polio_campaign2.round_level_vaccines_list, [self.mopv2, self.nopv2_bopv])
        self.assertEqual(self.polio_campaign2.sub_activity_level_vaccines_list, [])
        self.assertEqual(self.polio_campaign2.vaccines_extended_list, [self.mopv2, self.nopv2_bopv])
        self.assertEqual(self.polio_campaign2.vaccines_full_list, [self.mopv2, self.nopv2_bopv])
        self.assertEqual(self.polio_campaign2.single_vaccines_extended_list, [self.bopv, self.mopv2, self.nopv2])
        self.assertEqual(self.polio_campaign2.single_vaccines_full_list, [self.bopv, self.mopv2, self.nopv2])

    def test_vaccine_properties_campaign_scope(self):
        # strings
        self.assertEqual(self.polio_campaign.vaccines, f"{self.mopv2}")
        self.assertEqual(self.polio_campaign.vaccines_extended, f"{self.mopv2}")
        self.assertEqual(self.polio_campaign.vaccines_full, f"{self.mopv2}")
        self.assertEqual(self.polio_campaign.single_vaccines_extended, f"{self.mopv2}")
        self.assertEqual(self.polio_campaign.single_vaccines_full, f"{self.mopv2}")
        # lists
        self.assertEqual(self.polio_campaign.campaign_level_vaccines_list, [self.mopv2])
        self.assertEqual(self.polio_campaign.round_level_vaccines_list, [])
        self.assertEqual(self.polio_campaign.sub_activity_level_vaccines_list, [])
        self.assertEqual(self.polio_campaign.vaccines_extended_list, [self.mopv2])
        self.assertEqual(self.polio_campaign.single_vaccines_extended_list, [self.mopv2])
        self.assertEqual(self.polio_campaign.vaccines_full_list, [self.mopv2])
        self.assertEqual(self.polio_campaign.single_vaccines_full_list, [self.mopv2])

    def test_vaccine_properties_campaign_scope_with_sub_activities(self):
        # strings
        self.assertEqual(self.polio_campaign3.vaccines, f"{self.mopv2}")
        self.assertEqual(self.polio_campaign3.vaccines_extended, f"{self.mopv2}")
        self.assertEqual(self.polio_campaign3.vaccines_full, f"{self.bopv}, {self.mopv2}, {self.nopv2_bopv}")
        self.assertEqual(self.polio_campaign3.single_vaccines_extended, f"{self.mopv2}")
        self.assertEqual(self.polio_campaign3.single_vaccines_full, f"{self.bopv}, {self.mopv2}, {self.nopv2}")
        # lists
        self.assertEqual(self.polio_campaign3.campaign_level_vaccines_list, [self.mopv2])
        self.assertEqual(self.polio_campaign3.round_level_vaccines_list, [])
        self.assertEqual(self.polio_campaign3.sub_activity_level_vaccines_list, [self.bopv, self.nopv2_bopv])
        self.assertEqual(self.polio_campaign3.vaccines_extended_list, [self.mopv2])
        self.assertEqual(self.polio_campaign3.single_vaccines_extended_list, [self.mopv2])
        self.assertEqual(self.polio_campaign3.vaccines_full_list, [self.bopv, self.mopv2, self.nopv2_bopv])
        self.assertEqual(self.polio_campaign3.single_vaccines_full_list, [self.bopv, self.mopv2, self.nopv2])

    def test_vaccine_properties_with_separate_scopes_per_round_with_subactivities(self):
        # strings
        self.assertEqual(self.polio_campaign4.vaccines, f"{self.bopv}, {self.mopv2}")
        self.assertEqual(self.polio_campaign4.vaccines_extended, f"{self.bopv}, {self.mopv2}")
        self.assertEqual(self.polio_campaign4.vaccines_full, f"{self.bopv}, {self.mopv2}, {self.nopv2_bopv}")
        self.assertEqual(self.polio_campaign2.single_vaccines_extended, f"{self.bopv}, {self.mopv2}, {self.nopv2}")
        # lists
        self.assertEqual(self.polio_campaign4.campaign_level_vaccines_list, [])
        self.assertEqual(self.polio_campaign4.round_level_vaccines_list, [self.bopv, self.mopv2])
        self.assertEqual(self.polio_campaign4.sub_activity_level_vaccines_list, [self.mopv2, self.nopv2_bopv])
        self.assertEqual(self.polio_campaign4.vaccines_extended_list, [self.bopv, self.mopv2])
        self.assertEqual(self.polio_campaign4.vaccines_full_list, [self.bopv, self.mopv2, self.nopv2_bopv])
        self.assertEqual(self.polio_campaign4.single_vaccines_extended_list, [self.bopv, self.mopv2])
        self.assertEqual(self.polio_campaign4.single_vaccines_full_list, [self.bopv, self.mopv2, self.nopv2])

    def test_round_vaccine_properties_no_subactivities(self):
        # strings
        self.assertEqual(self.polio2_round_1.vaccine_names, f"{self.mopv2}")
        self.assertEqual(self.polio2_round_1.single_vaccine_names, f"{self.mopv2}")
        self.assertEqual(self.polio2_round_1.vaccine_names_extended, f"{self.mopv2}")
        self.assertEqual(self.polio2_round_1.single_vaccine_names_extended, f"{self.mopv2}")
        self.assertEqual(self.polio2_round_1.subactivities_vaccine_names, f"")
        self.assertEqual(self.polio2_round_1.subactivities_single_vaccine_names, f"")

        self.assertEqual(self.polio2_round_2.vaccine_names, f"{self.nopv2_bopv}")
        self.assertEqual(self.polio2_round_2.single_vaccine_names, f"{self.bopv}, {self.nopv2}")
        self.assertEqual(self.polio2_round_2.vaccine_names_extended, f"{self.nopv2_bopv}")
        self.assertEqual(self.polio2_round_2.single_vaccine_names_extended, f"{self.bopv}, {self.nopv2}")
        self.assertEqual(self.polio2_round_2.subactivities_vaccine_names, f"")
        self.assertEqual(self.polio2_round_2.subactivities_single_vaccine_names, f"")

        # lists
        self.assertEqual(self.polio2_round_1.vaccine_list, [self.mopv2])
        self.assertEqual(self.polio2_round_1.single_vaccine_list, [self.mopv2])
        self.assertEqual(self.polio2_round_1.vaccine_list_extended, [self.mopv2])
        self.assertEqual(self.polio2_round_1.single_vaccine_list_extended, [self.mopv2])
        self.assertEqual(self.polio2_round_1.subactivities_vaccine_list, [])
        self.assertEqual(self.polio2_round_1.subactivities_single_vaccine_list, [])

        self.assertEqual(self.polio2_round_2.vaccine_list, [self.nopv2_bopv])
        self.assertEqual(self.polio2_round_2.single_vaccine_list, [self.bopv, self.nopv2])
        self.assertEqual(self.polio2_round_2.vaccine_list_extended, [self.nopv2_bopv])
        self.assertEqual(self.polio2_round_2.single_vaccine_list_extended, [self.bopv, self.nopv2])
        self.assertEqual(self.polio2_round_2.subactivities_vaccine_list, [])
        self.assertEqual(self.polio2_round_2.subactivities_single_vaccine_list, [])

    def test_round_vaccine_properties_with_subactivities(self):
        # strings
        self.assertEqual(self.polio4_round_1.vaccine_names, f"{self.mopv2}")
        self.assertEqual(self.polio4_round_1.single_vaccine_names, f"{self.mopv2}")
        self.assertEqual(self.polio4_round_1.vaccine_names_extended, f"{self.mopv2}, {self.nopv2_bopv}")
        self.assertEqual(self.polio4_round_1.single_vaccine_names_extended, f"{self.bopv}, {self.mopv2}, {self.nopv2}")
        self.assertEqual(self.polio4_round_1.subactivities_vaccine_names, f"{self.nopv2_bopv}")
        self.assertEqual(self.polio4_round_1.subactivities_single_vaccine_names, f"{self.bopv}, {self.nopv2}")

        self.assertEqual(self.polio4_round_2.vaccine_names, f"{self.bopv}")
        self.assertEqual(self.polio4_round_2.single_vaccine_names, f"{self.bopv}")
        self.assertEqual(self.polio4_round_2.vaccine_names_extended, f"{self.bopv}, {self.mopv2}")
        self.assertEqual(self.polio4_round_2.single_vaccine_names_extended, f"{self.bopv}, {self.mopv2}")
        self.assertEqual(self.polio4_round_2.subactivities_vaccine_names, f"{self.mopv2}")
        self.assertEqual(self.polio4_round_2.subactivities_single_vaccine_names, f"{self.mopv2}")

        # lists
        self.assertEqual(self.polio4_round_1.vaccine_list, [self.mopv2])
        self.assertEqual(self.polio4_round_1.single_vaccine_list, [self.mopv2])
        self.assertEqual(self.polio4_round_1.vaccine_list_extended, [self.mopv2, self.nopv2_bopv])
        self.assertEqual(self.polio4_round_1.single_vaccine_list_extended, [self.bopv, self.mopv2, self.nopv2])
        self.assertEqual(self.polio4_round_1.subactivities_vaccine_list, [self.nopv2_bopv])
        self.assertEqual(self.polio4_round_1.subactivities_single_vaccine_list, [self.bopv, self.nopv2])

        self.assertEqual(self.polio4_round_2.vaccine_list, [self.bopv])
        self.assertEqual(self.polio4_round_2.single_vaccine_list, [self.bopv])
        self.assertEqual(self.polio4_round_2.vaccine_list_extended, [self.bopv, self.mopv2])
        self.assertEqual(self.polio4_round_2.single_vaccine_list_extended, [self.bopv, self.mopv2])
        self.assertEqual(self.polio4_round_2.subactivities_vaccine_list, [self.mopv2])
        self.assertEqual(self.polio4_round_2.subactivities_single_vaccine_list, [self.mopv2])

    def test_subactivities_properties(self):
        self.assertEqual(self.polio3_round_1_sub_activity1.vaccine_names, f"{self.nopv2_bopv}")
        self.assertEqual(self.polio3_round_1_sub_activity1.vaccine_list, [self.nopv2_bopv])
        self.assertEqual(self.polio3_round_1_sub_activity1.single_vaccine_names, f"{self.bopv}, {self.nopv2}")
        self.assertEqual(self.polio3_round_1_sub_activity1.single_vaccine_list, [self.bopv, self.nopv2])

        self.assertEqual(self.polio3_round_2_sub_activity1.vaccine_names, f"{self.bopv}")
        self.assertEqual(self.polio3_round_2_sub_activity1.vaccine_list, [self.bopv])
        self.assertEqual(self.polio3_round_2_sub_activity1.single_vaccine_names, f"{self.bopv}")
        self.assertEqual(self.polio3_round_2_sub_activity1.single_vaccine_list, [self.bopv])

        self.assertEqual(self.polio4_round_1_sub_activity1.vaccine_names, f"{self.nopv2_bopv}")
        self.assertEqual(self.polio4_round_1_sub_activity1.vaccine_list, [self.nopv2_bopv])
        self.assertEqual(self.polio4_round_1_sub_activity1.single_vaccine_names, f"{self.bopv}, {self.nopv2}")
        self.assertEqual(self.polio4_round_1_sub_activity1.single_vaccine_list, [self.bopv, self.nopv2])

        self.assertEqual(self.polio4_round_2_sub_activity1.vaccine_names, f"{self.mopv2}")
        self.assertEqual(self.polio4_round_2_sub_activity1.vaccine_list, [self.mopv2])
        self.assertEqual(self.polio4_round_2_sub_activity1.single_vaccine_names, f"{self.mopv2}")
        self.assertEqual(self.polio4_round_2_sub_activity1.single_vaccine_list, [self.mopv2])
