from iaso.models.payments import PaymentStatuses
from iaso.test import APITestCase
from iaso.models import PaymentLot, Payment, OrgUnit, OrgUnitType, SourceVersion, Account, DataSource


class TestPaymentLotsFilters(APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        data_source = DataSource.objects.create(name="Data source")
        version = SourceVersion.objects.create(number=1, data_source=data_source)
        account = Account.objects.create(name="Account", default_version=version)
        cls.user = cls.create_user_with_profile(username="user", account=account)
        cls.org_unit_type = OrgUnitType.objects.create(name="Hospital")
        cls.org_unit = OrgUnit.objects.create(name="Test Hospital", org_unit_type=cls.org_unit_type)
        cls.payment_lot = PaymentLot.objects.create(name="Test Payment Lot", created_by=cls.user)
        cls.payment = Payment.objects.create(
            user=cls.user,
            payment_lot=cls.payment_lot,
            status=PaymentStatuses.PAID,
        )
        cls.user_with_perm = cls.create_user_with_profile(
            username="user_with_perm",
            account=account,
            permissions=["iaso_org_unit_change_request_review", "iaso_payments"],
        )

    def test_filter_on_users(self):
        self.client.force_authenticate(self.user_with_perm)
        response = self.client.get("/api/payments/lots/" + f"?users={self.user.id}")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            all(payment_lot["created_by"]["id"] == self.user.id for payment_lot in response.data["results"])
        )

    def test_filter_on_parent(self):
        self.client.force_authenticate(self.user_with_perm)
        response = self.client.get("/api/payments/lots/" + f"?parent_id={self.org_unit.id}")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            all(
                org_unit["id"] == self.org_unit.id
                for payment_lot in response.data["results"]
                for org_unit in payment_lot["payments"][0]["org_unit"]
            )
        )

    def test_filter_on_start_end_date(self):
        self.client.force_authenticate(self.user_with_perm)
        response = self.client.get("/api/payments/lots/" + "?created_at_after=2023-01-01&created_at_before=2023-12-31")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            all(
                "2023-01-01" <= payment_lot["created_at"][:10] <= "2023-12-31"
                for payment_lot in response.data["results"]
            )
        )

    def test_filter_on_status(self):
        self.client.force_authenticate(self.user_with_perm)
        response = self.client.get("/api/payments/lots/" + "?status=PAID")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            all(
                payment["status"] == "PAID"
                for payment_lot in response.data["results"]
                for payment in payment_lot["payments"]
            )
        )
