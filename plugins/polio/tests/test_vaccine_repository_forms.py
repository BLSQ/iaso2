import datetime

from django.contrib.auth.models import AnonymousUser
from django.utils.timezone import now

from iaso import models as m
from iaso.test import APITestCase
from plugins.polio import models as pm
from plugins.polio.tests.api.test import PolioTestCaseMixin

BASE_URL = "/api/polio/vaccine/repository/"


class VaccineRepositoryFormsAPITestCase(APITestCase, PolioTestCaseMixin):
    @classmethod
    def setUp(cls):
        cls.data_source = m.DataSource.objects.create(name="Default source")
        cls.source_version_1 = m.SourceVersion.objects.create(data_source=cls.data_source, number=1)
        cls.account = m.Account.objects.create(name="polio", default_version=cls.source_version_1)
        cls.now = now()

        cls.org_unit_type_country = m.OrgUnitType.objects.create(name="Country", category="COUNTRY")
        cls.org_unit_type_district = m.OrgUnitType.objects.create(name="District")

        cls.campaign, cls.campaign_round_1, _, _, cls.testland, _ = cls.create_campaign(
            obr_name="Test Campaign",
            account=cls.account,
            source_version=cls.source_version_1,
            country_ou_type=cls.org_unit_type_country,
            country_name="Testland",
            district_ou_type=cls.org_unit_type_district,
        )
        cls.campaign_round_1.started_at = datetime.date(2021, 1, 4)
        cls.campaign_round_1.save()

        cls.campaign_no_vrf, cls.campaign_no_vrf_round_1, _, _, _, _ = cls.create_campaign(
            obr_name="No VRF",
            account=cls.account,
            source_version=cls.source_version_1,
            country_ou_type=cls.org_unit_type_country,
            country_name="Testland",
            district_ou_type=cls.org_unit_type_district,
        )
        # Has same country as cls.campaign, but no vrf. Should not appear in any API payload
        cls.campaign_no_vrf.country = cls.testland
        cls.campaign_no_vrf.save()
        cls.campaign_deleted_vrf, cls.campaign_deleted_vrf_round_1, _, _, _, _ = cls.create_campaign(
            obr_name="DELETED VRF",
            account=cls.account,
            source_version=cls.source_version_1,
            country_ou_type=cls.org_unit_type_country,
            country_name="Testland",
            district_ou_type=cls.org_unit_type_district,
        )
        # Has same country as cls.campaign, but no vrf. Should not appear in any API payload
        cls.campaign_deleted_vrf.country = cls.testland
        cls.campaign_deleted_vrf.save()

        cls.deleted_vaccine_request_form = pm.VaccineRequestForm.objects.create(
            campaign=cls.campaign_no_vrf,
            vaccine_type=pm.VACCINES[0][0],
            date_vrf_reception=cls.now - datetime.timedelta(days=30),
            date_vrf_signature=cls.now - datetime.timedelta(days=20),
            date_dg_approval=cls.now - datetime.timedelta(days=10),
            quantities_ordered_in_doses=500,
            deleted_at=cls.now,
        )
        cls.deleted_vaccine_request_form.rounds.set([cls.campaign_deleted_vrf_round_1])

        cls.zambia = m.OrgUnit.objects.create(
            org_unit_type=cls.org_unit_type_country,
            version=cls.source_version_1,
            name="Zambia",
            validation_status=m.OrgUnit.VALIDATION_VALID,
            source_ref="ZambiaRef",
        )

        # Create campaign type
        cls.polio_type, _ = pm.CampaignType.objects.get_or_create(name="Polio")

        cls.campaign.campaign_types.add(cls.polio_type)

        # Create vaccine request form
        cls.vaccine_request_form = pm.VaccineRequestForm.objects.create(
            campaign=cls.campaign,
            vaccine_type=pm.VACCINES[0][0],
            date_vrf_reception=cls.now - datetime.timedelta(days=30),
            date_vrf_signature=cls.now - datetime.timedelta(days=20),
            date_dg_approval=cls.now - datetime.timedelta(days=10),
            quantities_ordered_in_doses=500,
        )
        cls.vaccine_request_form.rounds.set([cls.campaign_round_1])

        # Create users
        cls.anon = AnonymousUser()
        cls.user = cls.create_user_with_profile(username="user", account=cls.account)

    def test_anonymous_user_can_see_list(self):
        """Test that anonymous users can access the list endpoint"""
        self.client.force_authenticate(user=self.anon)
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, 200)

    def test_authenticated_user_can_see_list(self):
        """Test that authenticated users can access the list endpoint"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, 200)

    def test_list_only_returns_campaigns_with_vrf_or_forma(self):
        forma_campaign, forma_rnd1, _, _, _, _ = self.create_campaign(
            obr_name="FormA_Campaign",
            account=self.account,
            source_version=self.source_version_1,
            country_ou_type=self.org_unit_type_country,
            country_name="Testland",
            district_ou_type=self.org_unit_type_district,
        )
        forma_campaign.country = self.testland
        forma_campaign.campaign_types.add(self.polio_type)

        forma_campaign.save()

        vaccine_stock = pm.VaccineStock.objects.create(
            account=self.account, country=self.testland, vaccine=pm.VACCINES[0][0]
        )
        vaccine_stock.save()

        forma = pm.OutgoingStockMovement.objects.create(
            campaign=forma_campaign,
            vaccine_stock=vaccine_stock,
            round=forma_rnd1,
            report_date=self.now,
            form_a_reception_date=self.now,
            usable_vials_used=500,
            missing_vials=0,
        )
        forma.save()

        self.client.force_authenticate(user=self.user)
        response = self.client.get(BASE_URL)
        data = self.assertJSONResponse(response, 200)
        results = data["results"]
        campaign_names = [r["campaign_obr_name"] for r in results]
        self.assertNotIn(self.campaign_no_vrf.obr_name, campaign_names)
        self.assertNotIn(self.campaign_deleted_vrf.obr_name, campaign_names)
        self.assertIn(forma_campaign.obr_name, campaign_names)

    def test_list_response_structure(self):
        """Test the structure of the list response"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(BASE_URL)
        data = response.json()

        # Check pagination fields
        self.assertIn("count", data)
        self.assertIn("results", data)

        # Check result fields
        result = data["results"][0]
        self.assertIn("country_name", result)
        self.assertIn("campaign_obr_name", result)
        self.assertIn("round_id", result)
        self.assertIn("number", result)
        self.assertIn("start_date", result)
        self.assertIn("end_date", result)
        self.assertIn("vrf_data", result)
        self.assertIn("pre_alert_data", result)
        self.assertIn("form_a_data", result)

    def test_rounds_are_split_by_vaccine(self):
        campaign2, campaign2_rnd_1, campaign2_rnd_2, campaign2_rnd_3, _, district = self.create_campaign(
            obr_name="Test scopes",
            account=self.account,
            source_version=self.source_version_1,
            country_ou_type=self.org_unit_type_country,
            country_name="WillBeIgnored",
            district_ou_type=self.org_unit_type_district,
            district_name="ZDistrict",
        )
        campaign2.campaign_types.add(self.polio_type)
        campaign2.country = self.zambia
        scope_group = m.Group.objects.create(name="campaign_scope", source_version=self.source_version_1)
        scope_group.org_units.set([district])  # FIXME: we should actually have children org units
        scope = pm.CampaignScope.objects.create(campaign=campaign2, vaccine=pm.VACCINES[1][0], group=scope_group)

        vaccine_request_form_vaccine1 = pm.VaccineRequestForm.objects.create(
            campaign=campaign2,
            vaccine_type=pm.VACCINES[0][0],
            date_vrf_reception=self.now - datetime.timedelta(days=30),
            date_vrf_signature=self.now - datetime.timedelta(days=20),
            date_dg_approval=self.now - datetime.timedelta(days=10),
            quantities_ordered_in_doses=500,
        )
        vaccine_request_form_vaccine1.rounds.set([campaign2_rnd_1, campaign2_rnd_2, campaign2_rnd_3])
        vaccine_request_form_vaccine2 = pm.VaccineRequestForm.objects.create(
            campaign=campaign2,
            vaccine_type=pm.VACCINES[1][0],
            date_vrf_reception=self.now - datetime.timedelta(days=30),
            date_vrf_signature=self.now - datetime.timedelta(days=20),
            date_dg_approval=self.now - datetime.timedelta(days=10),
            quantities_ordered_in_doses=500,
        )
        vaccine_request_form_vaccine2.rounds.set([campaign2_rnd_1, campaign2_rnd_2, campaign2_rnd_3])

        self.client.force_authenticate(user=self.user)

        response = self.client.get(f"{BASE_URL}?campaign={campaign2.obr_name}&order=number")
        data = response.json()
        self.assertEqual(len(data["results"]), 6)  # 3 rounds * 2 vaccines = 6
        # Check first 2 entrieds are the same round...
        self.assertEqual(data["results"][0]["campaign_obr_name"], campaign2.obr_name)
        self.assertEqual(data["results"][0]["number"], 1)
        self.assertEqual(data["results"][1]["campaign_obr_name"], campaign2.obr_name)
        self.assertEqual(data["results"][1]["number"], 1)
        # ... but not the same vaccine
        self.assertNotEqual(data["results"][0]["vaccine_name"], data["results"][1]["vaccine_name"])
        # Check that each is one of the 2 expected vaccines
        self.assertTrue(data["results"][0]["vaccine_name"] in [pm.VACCINES[0][0], pm.VACCINES[1][0]])
        self.assertTrue(data["results"][1]["vaccine_name"] in [pm.VACCINES[0][0], pm.VACCINES[1][0]])

    def test_ordering(self):
        """Test ordering functionality"""
        # Create another country and campaign for ordering test

        campaign2, campaign2_round, campaign2_rnd2, campaign2_rnd3, _, _ = self.create_campaign(
            obr_name="Another Campaign",
            account=self.account,
            source_version=self.source_version_1,
            country_ou_type=self.org_unit_type_country,
            country_name="WillBeIgnored",
            district_ou_type=self.org_unit_type_district,
            district_name="ZDistrict",
        )
        campaign2.campaign_types.add(self.polio_type)
        campaign2.initial_org_unit = self.zambia
        campaign2.country = self.zambia
        campaign2.save()
        campaign2_round.number = 1
        campaign2_round.save()

        vrf2 = pm.VaccineRequestForm.objects.create(
            campaign=campaign2,
            vaccine_type=pm.VACCINES[0][0],
            date_vrf_reception=self.now,
            date_vrf_signature=self.now,
            date_dg_approval=self.now,
            quantities_ordered_in_doses=500,
        )
        vrf2.rounds.set([campaign2_round, campaign2_rnd2, campaign2_rnd3])

        self.client.force_authenticate(user=self.user)

        # Test default ordering => -campaign start date
        response = self.client.get(f"{BASE_URL}")
        data = response.json()
        self.assertEqual(data["results"][0]["campaign_obr_name"], "Test Campaign")
        self.assertEqual(data["results"][3]["campaign_obr_name"], "Another Campaign")

        # Test ordering by campaign name
        response = self.client.get(f"{BASE_URL}?order=campaign__obr_name")
        data = response.json()
        self.assertEqual(data["results"][0]["campaign_obr_name"], "Another Campaign")
        self.assertEqual(data["results"][3]["campaign_obr_name"], "Test Campaign")

        # Test reverse ordering by campaign name
        response = self.client.get(f"{BASE_URL}?order=-campaign__obr_name")
        data = response.json()
        self.assertEqual(data["results"][0]["campaign_obr_name"], "Test Campaign")
        self.assertEqual(data["results"][3]["campaign_obr_name"], "Another Campaign")

        # Test ordering by round number
        response = self.client.get(f"{BASE_URL}?order=number")
        data = response.json()
        self.assertEqual(data["results"][0]["number"], 1)
        self.assertEqual(data["results"][3]["number"], 3)

        # Test reverse ordering by round number
        response = self.client.get(f"{BASE_URL}?order=-number")
        data = response.json()
        self.assertEqual(data["results"][0]["number"], 3)
        self.assertEqual(data["results"][3]["number"], 1)

        # Test ordering by country name
        response = self.client.get(f"{BASE_URL}?order=campaign__country__name")
        data = response.json()
        self.assertEqual(data["results"][0]["country_name"], "Testland")
        self.assertEqual(data["results"][3]["country_name"], "Zambia")

        # Test reverse ordering by country name
        response = self.client.get(f"{BASE_URL}?order=-campaign__country__name")
        data = response.json()
        self.assertEqual(data["results"][0]["country_name"], "Zambia")
        self.assertEqual(data["results"][3]["country_name"], "Testland")

        # Test ordering by start date
        response = self.client.get(f"{BASE_URL}?order=started_at")
        data = response.json()
        self.assertEqual(data["results"][0]["start_date"], campaign2_round.started_at.strftime("%Y-%m-%d"))
        self.assertEqual(data["results"][1]["start_date"], self.campaign_round_1.started_at.strftime("%Y-%m-%d"))

        # Test reverse ordering by start date
        response = self.client.get(f"{BASE_URL}?order=-started_at")
        data = response.json()
        self.assertEqual(data["results"][0]["start_date"], campaign2_rnd3.started_at.strftime("%Y-%m-%d"))
        self.assertEqual(data["results"][2]["start_date"], self.campaign_round_1.started_at.strftime("%Y-%m-%d"))
        self.assertEqual(data["results"][3]["start_date"], campaign2_round.started_at.strftime("%Y-%m-%d"))

    def test_filtering(self):
        """Test filtering functionality of VaccineReportingViewSet"""
        # Create test data
        campaign2, campaign2_round, campaign2_rnd2, campaign2_rnd3, _, _ = self.create_campaign(
            obr_name="Another Campaign",
            account=self.account,
            source_version=self.source_version_1,
            country_ou_type=self.org_unit_type_country,
            country_name="WillBeIgnored",
            district_ou_type=self.org_unit_type_district,
            district_name="ZDistrict",
            vaccine=pm.VACCINES[1][0],
        )
        campaign2_round.delete()
        campaign2_rnd2.delete()
        campaign2_rnd3.delete()
        campaign2.campaign_types.add(self.polio_type)
        campaign2.initial_org_unit = self.zambia
        campaign2.save()
        campaign2.campaign_types.add(self.polio_type)

        campaign2_round = pm.Round.objects.create(
            campaign=campaign2,
            started_at=datetime.date(2021, 2, 1),
            ended_at=datetime.date(2025, 1, 1),
            number=1,
        )

        campaign2.save()

        vrf2 = pm.VaccineRequestForm.objects.create(
            campaign=campaign2,
            date_vrf_signature=self.now,
            date_dg_approval=self.now,
            quantities_ordered_in_doses=500,
            vaccine_type=pm.VACCINES[1][0],
        )
        vrf2.rounds.set([campaign2_round])

        (
            preparing_campaign,
            preparing_campaign_round,
            preparing_campaign2_rnd2,
            preparing_campaign_rnd3,
            _,
            _,
        ) = self.create_campaign(
            obr_name="Preparing Campaign",
            account=self.account,
            source_version=self.source_version_1,
            country_ou_type=self.org_unit_type_country,
            country_name="WillBeIgnored",
            district_ou_type=self.org_unit_type_district,
            district_name="YDistrict",
        )
        preparing_campaign.campaign_types.add(self.polio_type)
        preparing_campaign.initial_org_unit = self.zambia
        preparing_campaign.save()
        preparing_campaign_round.delete()
        preparing_campaign2_rnd2.delete()
        preparing_campaign_rnd3.delete()

        preparing_campaign_round = pm.Round.objects.create(
            campaign=preparing_campaign,
            started_at=datetime.date(2025, 2, 1),
            ended_at=datetime.date(2025, 2, 28),
            number=1,
        )

        vrf_for_preparing_campaign = pm.VaccineRequestForm.objects.create(
            campaign=preparing_campaign,
            date_vrf_signature=self.now,
            date_dg_approval=self.now,
            quantities_ordered_in_doses=500,
            vaccine_type=pm.VACCINES[0][0],
        )
        vrf_for_preparing_campaign.rounds.set([preparing_campaign_round])

        self.client.force_authenticate(user=self.user)

        # Test filtering by country
        response = self.client.get(f"{BASE_URL}?countries={self.zambia.id}")
        data = response.json()
        self.assertEqual(len(data["results"]), 2)
        self.assertTrue(all(result["country_name"] == "Zambia" for result in data["results"]))

        # Test filtering by campaign name
        response = self.client.get(f"{BASE_URL}?campaign=Test Campaign")
        data = response.json()
        # VRF covers only round 1, so there should be only one result
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["campaign_obr_name"], "Test Campaign")
        self.assertEqual(data["results"][0]["number"], 1)

        # Test filtering by file type - VRF
        response = self.client.get(f"{BASE_URL}?file_type=VRF")
        data = response.json()
        self.assertEqual(
            len(data["results"]), 3
        )  # 1 round for campaign 2, 1 for self.campaign. 1 for preparing_campaign

        # Test filtering by country block
        country_group = self.zambia.groups.first()
        if country_group:
            response = self.client.get(f"{BASE_URL}?country_block={country_group.id}")
            data = response.json()
            self.assertEqual(len(data["results"]), 2)
            self.assertTrue(all(result["country_name"] == "Zambia" for result in data["results"]))

        # Test filtering by vaccine name
        response = self.client.get(f"{BASE_URL}?vaccine_name={pm.VACCINES[1][0]}")
        response = self.assertJSONResponse(response, 200)
        data = response["results"]
        self.assertEqual(len(data), 1)
        response = self.client.get(f"{BASE_URL}?vaccine_name={pm.VACCINES[0][0]}")
        response = self.assertJSONResponse(response, 200)
        data = response["results"]
        self.assertEqual(
            len(data), 2
        )  # Only 1 round of self.campaign is cvovered by the vrf, the others should be filtered out
