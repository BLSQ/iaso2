from iaso.models.base import Account
from iaso.test import APITestCase
from plugins.polio.models import SpreadSheetImport
from hat.menupermissions import models as permission


class SupplyChainDashboardsAPITestCase(APITestCase):
    @classmethod
    def setUp(cls):
        cls.url = "/api/polio/dashboards/preparedness_sheets/"
        cls.account = Account.objects.create(name="test account")
        cls.other_account = Account.objects.create(name="other account")
        cls.authorized_user = cls.create_user_with_profile(
            username="authorized",
            account=cls.account,
            permissions=[
                permission._POLIO,
            ],
        )
        cls.authorized_user_admin = cls.create_user_with_profile(
            username="authorized_admin",
            account=cls.account,
            permissions=[
                permission._POLIO_CONFIG,
            ],
        )
        cls.unauthorized_user = cls.create_user_with_profile(
            username="unAuthorized", account=cls.account, permissions=[]
        )
        cls.spreadsheet = SpreadSheetImport.objects.create(
            url="https://baconipsum.com/", spread_id="spread_id", content=[{"hello": "world"}]
        )

    def test_user_has_permission(self):
        self.client.force_authenticate(self.unauthorized_user)
        response = self.client.get(self.url)
        self.assertJSONResponse(response, 403)

        self.client.force_authenticate(self.authorized_user)
        response = self.client.get(self.url)
        self.assertJSONResponse(response, 200)

        self.client.force_authenticate(self.authorized_user_admin)
        response = self.client.get(self.url)
        self.assertJSONResponse(response, 200)

    def test_default_pagination_is_added(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(f"{self.url}/")
        data = self.assertJSONResponse(response, 200)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["limit"], 20)

    def test_max_page_size_is_enforced(self):
        default_max_page_size = 1000  # default value from EtlPaginator
        self.client.force_authenticate(self.user)
        response = self.client.get(f"{self.url}/?limit=2000&page=1")
        data = self.assertJSONResponse(response, 200)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["limit"], default_max_page_size)
