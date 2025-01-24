import typing

from iaso import models as m
from iaso.api.query_params import APP_ID
from iaso.test import APITestCase


class OrgUnitTypesAPITestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        ghi = m.Account.objects.create(name="Global Health Initiative")
        wha = m.Account.objects.create(name="Worldwide Health Aid")
        cls.ead = m.Project.objects.create(
            name="End All Diseases",
            app_id="ead",
            account=ghi,
            needs_authentication=True,
        )
        cls.esd = m.Project.objects.create(name="End Some Diseases", app_id="esd", account=wha)

        cls.jane = cls.create_user_with_profile(username="janedoe", account=ghi, permissions=["iaso_forms"])
        cls.john = cls.create_user_with_profile(username="johndoe", account=wha, permissions=["iaso_forms"])
        cls.reference_form = m.Form.objects.create(
            name="Hydroponics study", period_type=m.MONTH, single_per_period=True
        )
        cls.reference_form_update = m.Form.objects.create(
            name="Reference form update", period_type=m.MONTH, single_per_period=True
        )
        cls.reference_form_wrong_project = m.Form.objects.create(
            name="Reference form with wrong project", period_type=m.MONTH, single_per_period=True
        )
        cls.org_unit_type_1 = m.OrgUnitType.objects.create(name="Plop", short_name="Pl")

        cls.org_unit_type_2 = m.OrgUnitType.objects.create(name="Boom", short_name="Bo")
        cls.ead.unit_types.set([cls.org_unit_type_1, cls.org_unit_type_2])

        cls.ead.forms.add(cls.reference_form)
        cls.ead.forms.add(cls.reference_form_update)
        cls.ead.save()

        cls.esd.forms.add(cls.reference_form_wrong_project)
        cls.esd.save()

    def test_orgunittypes_list_without_auth_for_project_requiring_auth(self):
        """GET /orgunittypes/ without auth for project which requires it: 401"""

        response = self.client.get("/api/orgunittypes/", {APP_ID: self.ead.app_id})
        self.assertJSONResponse(response, 401)

    def test_orgunittypes_list_with_wrong_auth_for_project_requiring_auth(self):
        """GET /orgunittypes/ with wrong auth for project which requires it: 401"""

        self.client.force_authenticate(user=self.john)
        response = self.client.get("/api/orgunittypes/", {APP_ID: self.ead.app_id})
        self.assertJSONResponse(response, 401)

    def test_orgunittypes_list_with_auth_for_project_requiring_auth(self):
        """GET /orgunittypes/ with auth for project which requires it: 200"""

        self.client.force_authenticate(user=self.jane)
        response = self.client.get("/api/orgunittypes/", {APP_ID: self.ead.app_id})
        self.assertJSONResponse(response, 200)

    def test_org_unit_types_list_without_auth_or_app_id(self):
        """GET /orgunittypes/ without auth or app id should result in a 200 empty response"""

        response = self.client.get("/api/orgunittypes/")
        self.assertJSONResponse(response, 200)
        self.assertValidOrgUnitTypeListData(response.json(), 0)

    def test_org_unit_types_list_with_auth(self):
        """GET /orgunittypes/ without auth or app id should result in a 200 empty response"""

        self.client.force_authenticate(self.jane)
        response = self.client.get("/api/orgunittypes/")
        self.assertJSONResponse(response, 200)

        response_data = response.json()
        self.assertValidOrgUnitTypeListData(response_data, 2)
        for org_unit_type_data in response_data["orgUnitTypes"]:
            self.assertEqual(len(org_unit_type_data["projects"]), 1)

    def test_org_unit_types_retrieve_without_auth_or_app_id(self):
        """GET /orgunittypes/<org_unit_type_id>/ without auth or app id should result in a 200 empty response"""

        response = self.client.get(f"/api/orgunittypes/{self.org_unit_type_1.id}/")
        self.assertJSONResponse(response, 404)

    def test_org_unit_types_retrieve_ok(self):
        """GET /orgunittypes/<org_unit_type_id>/ happy path"""

        self.client.force_authenticate(self.jane)
        response = self.client.get(f"/api/orgunittypes/{self.org_unit_type_1.id}/")
        self.assertJSONResponse(response, 200)
        self.assertValidOrgUnitTypeData(response.json())

    def test_org_unit_type_create_no_auth(self):
        """POST /orgunittypes/ without auth: 401"""

        response = self.client.post("/api/orgunittypes/", data={}, format="json")
        self.assertJSONResponse(response, 401)

    def test_org_unit_type_create_invalid(self):
        """POST /orgunittypes/ without project ids: invalid"""

        self.client.force_authenticate(self.jane)
        response = self.client.post(
            "/api/orgunittypes/", data={"name": "", "depth": 1, "project_ids": []}, format="json"
        )
        self.assertJSONResponse(response, 400)
        self.assertHasError(response.json(), "name", "This field may not be blank.")
        self.assertHasError(response.json(), "short_name", "This field is required.")
        self.assertHasError(response.json(), "project_ids", "This list may not be empty.")

    def test_org_unit_type_create_invalid_wrong_project(self):
        """POST /orgunittypes/ without project ids: invalid"""

        self.client.force_authenticate(self.jane)
        response = self.client.post(
            "/api/orgunittypes/",
            data={
                "name": "Bimbam",
                "short_name": "Bi",
                "depth": 1,
                "project_ids": [self.esd.id],
                "sub_unit_type_ids": [],
                "allow_creating_sub_unit_type_ids": [],
            },
            format="json",
        )
        self.assertJSONResponse(response, 400)
        self.assertHasError(response.json(), "project_ids", "Invalid project ids")

    def test_org_unit_type_create_ok(self):
        """POST /orgunittypes/ with auth: 201 OK"""

        self.client.force_authenticate(self.jane)
        response = self.client.post(
            "/api/orgunittypes/",
            data={
                "name": "Bimbam",
                "short_name": "Bi",
                "depth": 1,
                "project_ids": [self.ead.id],
                "sub_unit_type_ids": [],
                "allow_creating_sub_unit_type_ids": [],
                "reference_form_id": 100,  # The old field should be ignored.
            },
            format="json",
        )

        org_unit_type_data = response.json()
        self.assertJSONResponse(response, 201)
        self.assertValidOrgUnitTypeData(org_unit_type_data)
        self.assertEqual(1, len(org_unit_type_data["projects"]))

    def test_org_unit_type_create_with_sub_unit_types_ok(self):
        """POST /orgunittypes/ with auth: 201 OK"""

        self.client.force_authenticate(self.jane)
        response = self.client.post(
            "/api/orgunittypes/",
            data={
                "name": "Bimbam",
                "short_name": "Bi",
                "depth": 1,
                "project_ids": [self.ead.id],
                "sub_unit_type_ids": [self.org_unit_type_1.id, self.org_unit_type_2.id],
                "allow_creating_sub_unit_type_ids": [],
            },
            format="json",
        )
        self.assertJSONResponse(response, 201)

        org_unit_type_data = response.json()
        self.assertValidOrgUnitTypeData(org_unit_type_data)
        self.assertEqual(1, len(org_unit_type_data["projects"]))
        self.assertEqual(2, len(org_unit_type_data["sub_unit_types"]))

    def test_org_unit_type_update_ok(self):
        """PUT /orgunittypes/<org_unit_type_id>: 200 OK"""

        self.client.force_authenticate(self.jane)
        response = self.client.put(
            f"/api/orgunittypes/{self.org_unit_type_1.id}/",
            data={
                "name": "Plop updated",
                "short_name": "Bi",
                "depth": 1,
                "project_ids": [self.ead.id],
                "sub_unit_type_ids": [],
                "allow_creating_sub_unit_type_ids": [],
            },
            format="json",
        )
        self.assertJSONResponse(response, 200)
        self.assertValidOrgUnitTypeData(response.json())

    def test_org_unit_type_update_with_reference_form_id_ok(self):
        """PUT /orgunittypes/<org_unit_type_id>: 200 OK"""

        self.client.force_authenticate(self.jane)
        response = self.client.put(
            f"/api/orgunittypes/{self.org_unit_type_1.id}/",
            data={
                "name": "Plop updated",
                "short_name": "Bi",
                "depth": 1,
                "project_ids": [self.ead.id],
                "sub_unit_type_ids": [],
                "allow_creating_sub_unit_type_ids": [],
            },
            format="json",
        )
        self.assertJSONResponse(response, 200)
        self.assertValidOrgUnitTypeData(response.json())

    def test_org_unit_type_partial_update_ok(self):
        """PATCH /orgunittypes/<org_unit_type_id>/: 200 OK"""

        self.client.force_authenticate(self.jane)
        response = self.client.patch(
            f"/api/orgunittypes/{self.org_unit_type_1.id}/", data={"short_name": "P"}, format="json"
        )
        self.assertJSONResponse(response, 200)
        self.assertValidOrgUnitTypeData(response.json())
        self.org_unit_type_1.refresh_from_db()
        self.assertEqual("P", self.org_unit_type_1.short_name)

    def test_org_unit_type_delete_ok(self):
        """DELETE /orgunittypes/<org_unit_type_id>: 200 OK"""

        self.client.force_authenticate(self.jane)
        response = self.client.delete(f"/api/orgunittypes/{self.org_unit_type_1.id}/", format="json")
        self.assertJSONResponse(response, 204)

    def assertValidOrgUnitTypeListData(self, list_data: typing.Mapping, expected_length: int, paginated: bool = False):
        self.assertValidListData(
            list_data=list_data, expected_length=expected_length, results_key="orgUnitTypes", paginated=paginated
        )

        for org_unit_type_data in list_data["orgUnitTypes"]:
            self.assertValidOrgUnitTypeData(org_unit_type_data)

    # noinspection DuplicatedCode
    def assertValidOrgUnitTypeData(self, org_unit_type_data):
        self.assertHasField(org_unit_type_data, "id", int)
        self.assertHasField(org_unit_type_data, "name", str)
        self.assertHasField(org_unit_type_data, "short_name", str)
        self.assertHasField(org_unit_type_data, "depth", int, optional=True)
        self.assertHasField(org_unit_type_data, "projects", list, optional=True)
        self.assertHasField(org_unit_type_data, "sub_unit_types", list, optional=True)
        self.assertHasField(org_unit_type_data, "created_at", float)

        if "projects" in org_unit_type_data:
            for project_data in org_unit_type_data["projects"]:
                self.assertValidProjectData(project_data)

        if "sub_unit_types" in org_unit_type_data:
            for sub_org_unit_type_data in org_unit_type_data["sub_unit_types"]:
                self.assertValidOrgUnitTypeData(sub_org_unit_type_data)
