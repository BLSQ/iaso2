import datetime

from iaso.models.base import Group
from iaso.models.org_unit import OrgUnitType
from iaso.test import APITestCase
from plugins.polio.models import SubActivity, SubActivityScope
from plugins.polio.tests.api.test import PolioTestCaseMixin

BASE_URL = "/api/polio/dashboards/subactivities"


class SubactivitiesAPITestCase(APITestCase, PolioTestCaseMixin):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.account, cls.data_source, cls.source_version, cls.project = cls.create_account_datasource_version_project(
            "Account", "Data source", "Project"
        )
        cls.user, cls.anon, cls.user_no_perms = cls.create_base_users(cls.account, ["iaso_polio"])
        cls.country_type = OrgUnitType.objects.create(name="COUNTRY", short_name="COUNTRY")
        cls.district_type = OrgUnitType.objects.create(name="DISTRICT", short_name="DISTRICT")
        cls.campaign, cls.rnd1, cls.rnd2, cls.rnd3, cls.country, cls.district = cls.create_campaign(
            obr_name="Test Campaign",
            account=cls.account,
            source_version=cls.source_version,
            country_ou_type=cls.country_type,
            district_ou_type=cls.district_type,
        )

        cls.sub_activity = SubActivity.objects.create(
            name="Test SubActivity",
            round=cls.rnd1,
            start_date=datetime.date(2022, 1, 1),
            end_date=datetime.date(2022, 1, 31),
        )
        cls.group = Group.objects.create(name="Test group", source_version=cls.source_version)
        cls.group.org_units.add(cls.district)

        cls.sub_activity_scope = SubActivityScope.objects.create(
            subactivity=cls.sub_activity, group=cls.group, vaccine="mOPV2"
        )

    def test_anonymous_user_cannot_get(self):
        self.client.force_authenticate(self.anon)
        response = self.client.get(f"{BASE_URL}/")
        self.assertEqual(response.status_code, 403)

    def test_default_pagination_is_added(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(f"{BASE_URL}/")
        data = self.assertJSONResponse(response, 200)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["limit"], 20)

    def test_max_page_size_is_enforced(self):
        default_max_page_size = 1000  # default value from EtlPaginator
        self.client.force_authenticate(self.user)
        response = self.client.get(f"{BASE_URL}/?limit=2000&page=1")
        data = self.assertJSONResponse(response, 200)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["limit"], default_max_page_size)

    def test_get_sub_activities(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(f"{BASE_URL}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], "Test SubActivity")
