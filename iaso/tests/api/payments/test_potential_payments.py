import datetime
from iaso.test import APITestCase
from iaso import models as m


class PotentialPaymentsViewSetAPITestCase(APITestCase):
    """
    Test actions on the ViewSet.
    """

    DT = datetime.datetime(2023, 10, 17, 17, 0, 0, 0, tzinfo=datetime.timezone.utc)

    @classmethod
    def setUpTestData(cls):
        data_source = m.DataSource.objects.create(name="Data source")
        version = m.SourceVersion.objects.create(number=1, data_source=data_source)
        org_unit_type = m.OrgUnitType.objects.create(name="Org unit type")
        org_unit = m.OrgUnit.objects.create(
            org_unit_type=org_unit_type, version=version, uuid="1539f174-4c53-499c-85de-7a58458c49ef"
        )
        other_org_unit = m.OrgUnit.objects.create(
            org_unit_type=org_unit_type, version=version, uuid="1539f174-4c53-499c-85de-7a58458c21gh"
        )

        account = m.Account.objects.create(name="Account", default_version=version)
        another_account = m.Account.objects.create(name="another_account", default_version=version)
        user_from_another_account = cls.create_user_with_profile(
            username="user_from_another_account", account=another_account
        )
        project = m.Project.objects.create(name="Project", account=account, app_id="foo.bar.baz")
        user = cls.create_user_with_profile(username="user", account=account)
        user_with_perm = cls.create_user_with_profile(
            username="user_with_perm",
            account=account,
            permissions=["iaso_org_unit_change_request_review", "iaso_payments"],
        )
        geo_limited_user = cls.create_user_with_profile(
            username="geo_limited_user",
            account=account,
            permissions=["iaso_org_unit_change_request_review", "iaso_payments"],
        )
        geo_limited_user.iaso_profile.org_units.set([other_org_unit])

        data_source.projects.set([project])
        org_unit_type.projects.set([project])
        user.iaso_profile.org_units.set([org_unit])

        cls.org_unit = org_unit
        cls.other_org_unit = other_org_unit
        cls.org_unit_type = org_unit_type
        cls.project = project
        cls.user = user
        cls.geo_limited_user = geo_limited_user
        cls.user_with_perm = user_with_perm
        cls.user_from_another_account = user_from_another_account
        cls.version = version

    def test_list_ok(self):
        # Create approved change requests for the users
        m.OrgUnitChangeRequest.objects.create(
            org_unit=self.org_unit, status=m.OrgUnitChangeRequest.Statuses.APPROVED, created_by=self.user
        )
        m.OrgUnitChangeRequest.objects.create(
            org_unit=self.org_unit,
            status=m.OrgUnitChangeRequest.Statuses.APPROVED,
            created_by=self.user_with_perm,
        )
        m.OrgUnitChangeRequest.objects.create(
            org_unit=self.org_unit,
            status=m.OrgUnitChangeRequest.Statuses.APPROVED,
            created_by=self.user_from_another_account,
        )

        self.client.force_authenticate(self.user_with_perm)

        response = self.client.get("/api/potential_payments/")
        self.assertJSONResponse(response, 200)
        # Check that the correct number of PotentialPayment objects were created
        self.assertEqual(2, len(response.data["results"]))
        # Check that the PotentialPayment objects were created for the correct users
        user_ids = [result["user"]["id"] for result in response.data["results"]]
        self.assertIn(self.user.id, user_ids)
        self.assertIn(self.user_with_perm.id, user_ids)
        self.assertNotIn(self.user_from_another_account.id, user_ids)

    def test_list_without_auth(self):
        response = self.client.get("/api/potential_payments/")
        self.assertJSONResponse(response, 401)

    def test_retrieve_not_allowed(self):
        potential_payment = m.PotentialPayment.objects.create(user=self.user)
        self.client.force_authenticate(self.user_with_perm)
        response = self.client.get(f"/api/potential_payments/{potential_payment.pk}/")
        self.assertJSONResponse(response, 404)
        self.assertEqual(response.data["detail"], "Retrieve operation is not allowed.")

    def test_retrieve_without_auth(self):
        potential_payment = m.PotentialPayment.objects.create(user=self.user)
        response = self.client.get(f"/api/potential_payments/{potential_payment.pk}/")
        self.assertJSONResponse(response, 401)

    def test_list_clears_old_potential_payments(self):
        m.PotentialPayment.objects.create(user=self.user)
        m.PotentialPayment.objects.create(user=self.user_with_perm)

        self.client.force_authenticate(self.user_with_perm)

        response = self.client.get("/api/potential_payments/")
        self.assertJSONResponse(response, 200)
        self.assertEqual(0, len(response.data["results"]))

    def test_list_creates_new_potential_payments(self):
        m.OrgUnitChangeRequest.objects.create(
            org_unit=self.org_unit, status=m.OrgUnitChangeRequest.Statuses.APPROVED, created_by=self.user
        )
        m.OrgUnitChangeRequest.objects.create(
            org_unit=self.org_unit,
            status=m.OrgUnitChangeRequest.Statuses.APPROVED,
            created_by=self.user_with_perm,
        )

        self.client.force_authenticate(self.user_with_perm)

        response = self.client.get("/api/potential_payments/")
        self.assertJSONResponse(response, 200)
        self.assertEqual(2, len(response.data["results"]))

    def test_list_does_not_create_potential_payments_for_existing_payments(self):
        change_request = m.OrgUnitChangeRequest.objects.create(
            org_unit=self.org_unit, status=m.OrgUnitChangeRequest.Statuses.APPROVED, created_by=self.user
        )
        payment = m.Payment.objects.create(user=self.user)  # specify a user here
        payment.change_requests.set([change_request])

        self.client.force_authenticate(self.user_with_perm)

        response = self.client.get("/api/potential_payments/")
        self.assertJSONResponse(response, 200)
        self.assertEqual(0, len(response.data["results"]))

    def test_geo_limited_user_cannot_see_change_requests_not_in_org_units(self):
        m.OrgUnitChangeRequest.objects.create(
            org_unit=self.org_unit, status=m.OrgUnitChangeRequest.Statuses.APPROVED, created_by=self.user
        )
        m.OrgUnitChangeRequest.objects.create(
            org_unit=self.org_unit,
            status=m.OrgUnitChangeRequest.Statuses.APPROVED,
            created_by=self.user_with_perm,
        )
        self.client.force_authenticate(self.geo_limited_user)
        response = self.client.get(f"/api/potential_payments/")
        self.assertJSONResponse(response, 200)
        data = response.json()
        results = data["results"]
        self.assertEqual(len(results), 2)
        for result in results:
            self.assertFalse(result["can_see_change_requests"])
            self.assertEqual(len(result["change_requests"]), 1)
            self.assertFalse(result["change_requests"][0]["can_see_change_request"])
