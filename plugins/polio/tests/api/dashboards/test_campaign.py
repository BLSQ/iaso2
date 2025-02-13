from rest_framework import status

from iaso.models.org_unit import OrgUnitType
from iaso.test import APITestCase
from plugins.polio.models import CampaignType
from plugins.polio.tests.api.test import PolioTestCaseMixin

BASE_URL = "/api/polio/dashboards/campaigns/"


class CampaignDashboardAPITestCase(APITestCase, PolioTestCaseMixin):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.account, cls.data_source, cls.source_version, cls.project = cls.create_account_datasource_version_project(
            "Account", "Data source", "Project"
        )
        cls.user, cls.anon, cls.user_no_perms = cls.create_base_users(cls.account, ["iaso_polio_budget"])
        cls.country_type = OrgUnitType.objects.create(name="COUNTRY", short_name="COUNTRY")
        cls.district_type = OrgUnitType.objects.create(name="DISTRICT", short_name="DISTRICT")
        # Campaign type.
        cls.polio_type = CampaignType.objects.get(name=CampaignType.POLIO)

        cls.campaign_1, cls.round_1, cls.round_2, cls.round_3, cls.country, cls.district = cls.create_campaign(
            obr_name="Test Campaign 1",
            account=cls.account,
            source_version=cls.source_version,
            country_ou_type=cls.country_type,
            district_ou_type=cls.district_type,
        )
        cls.campaign_1.campaign_types.set([cls.polio_type])

        cls.campaign_2, _, _, _, _, _ = cls.create_campaign(
            obr_name="Test Campaign 2",
            account=cls.account,
            source_version=cls.source_version,
            country_ou_type=cls.country_type,
            district_ou_type=cls.district_type,
        )
        cls.campaign_2.campaign_types.set([cls.polio_type])

        cls.campaign_3_deleted, _, _, _, _, _ = cls.create_campaign(
            obr_name="Test Campaign 3",
            account=cls.account,
            source_version=cls.source_version,
            country_ou_type=cls.country_type,
            district_ou_type=cls.district_type,
        )
        cls.campaign_3_deleted.campaign_types.set([cls.polio_type])
        cls.campaign_3_deleted.delete()

    def test_anonymous_user_cannot_get(self):
        self.client.force_authenticate(self.anon)
        response = self.client.get(f"{BASE_URL}")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_default_pagination_is_added(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(f"{BASE_URL}")
        data = self.assertJSONResponse(response, status.HTTP_200_OK)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["limit"], 20)

    def test_max_page_size_is_enforced(self):
        default_max_page_size = 1000  # default value from EtlPaginator
        self.client.force_authenticate(self.user)
        response = self.client.get(f"{BASE_URL}?limit=2000&page=1")
        data = self.assertJSONResponse(response, status.HTTP_200_OK)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["limit"], default_max_page_size)

    def test_list_campaigns(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(f"{BASE_URL}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["id"], str(self.campaign_1.id))
        self.assertEqual(results[0]["obr_name"], self.campaign_1.obr_name)
        self.assertEqual(results[1]["id"], str(self.campaign_2.id))
        self.assertEqual(results[1]["obr_name"], self.campaign_2.obr_name)

    def test_list_with_other_account(self):
        # Setting up new campaign with rounds and budget processes, in another account
        new_account, new_data_source, new_source_version, new_project = self.create_account_datasource_version_project(
            "New Account", "New Data source", "New Project"
        )
        new_campaign, new_round_1, new_round_2, new_round_3, self.country, self.district = self.create_campaign(
            obr_name="New Campaign",
            account=new_account,
            source_version=new_source_version,
            country_ou_type=self.country_type,
            district_ou_type=self.district_type,
        )
        new_campaign.campaign_types.set([self.polio_type])

        # Now we check that we only have the initial ones
        self.client.force_authenticate(self.user)
        response = self.client.get(f"{BASE_URL}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        self.assertEqual(len(results), 2)  # both from the setup
        self.assertEqual(results[0]["id"], str(self.campaign_1.id))
        self.assertEqual(results[0]["obr_name"], self.campaign_1.obr_name)
        self.assertEqual(results[1]["id"], str(self.campaign_2.id))
        self.assertEqual(results[1]["obr_name"], self.campaign_2.obr_name)
