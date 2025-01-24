import typing

from django.core.files import File
from django.utils.timezone import now

from iaso import models as m
from iaso.api.common import CONTENT_TYPE_XLSX
from iaso.api.query_params import APP_ID
from iaso.models import Form, OrgUnit, Instance
from iaso.test import APITestCase

from iaso.models import (
    Mapping,
    AGGREGATE,
)


class FormsAPITestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.now = now()

        star_wars = m.Account.objects.create(name="Star Wars")
        marvel = m.Account.objects.create(name="Marvel")

        cls.yoda = cls.create_user_with_profile(username="yoda", account=star_wars, permissions=["iaso_forms"])
        cls.raccoon = cls.create_user_with_profile(username="raccoon", account=marvel, permissions=["iaso_forms"])
        cls.iron_man = cls.create_user_with_profile(username="iron_man", account=marvel)

        sw_source = m.DataSource.objects.create(name="Galactic Empire")
        cls.sw_source = sw_source
        sw_version = m.SourceVersion.objects.create(data_source=sw_source, number=1)
        star_wars.default_version = sw_version
        star_wars.save()
        cls.sw_version = sw_version

        cls.jedi_council = m.OrgUnitType.objects.create(name="Jedi Council", short_name="Cnc")
        cls.jedi_academy = m.OrgUnitType.objects.create(name="Jedi Academy", short_name="Aca")
        cls.sith_guild = m.OrgUnitType.objects.create(name="Sith guild", short_name="Sith")

        cls.project_1 = m.Project.objects.create(
            name="Hydroponic gardens",
            app_id="stars.empire.agriculture.hydroponics",
            account=star_wars,
            needs_authentication=True,
        )
        cls.project_2 = m.Project.objects.create(
            name="New Land Speeder concept", app_id="stars.empire.agriculture.land_speeder", account=star_wars
        )

        cls.form_1 = m.Form.objects.create(name="Hydroponics study", created_at=cls.now)

        cls.project_3 = m.Project.objects.create(name="Kotor", app_id="knights.of.the.old.republic", account=star_wars)

        cls.jedi_council_corruscant = m.OrgUnit.objects.create(
            name="Coruscant Jedi Council",
            source_ref="jedi_council_corruscant_ref",
            version=sw_version,
            validation_status="VALID",
        )

        cls.form_2 = m.Form.objects.create(
            name="Hydroponic public survey",
            form_id="sample2",
            device_field="deviceid",
            location_field="geoloc",
            period_type="QUARTER",
            single_per_period=True,
            created_at=cls.now,
        )
        cls.form_2.form_versions.create(file=cls.create_file_mock(name="testf1.xml"), version_id="2020022401")
        cls.form_2.org_unit_types.add(cls.jedi_council)
        cls.form_2.org_unit_types.add(cls.jedi_academy)

        cls.form_2.instances.create(file=cls.create_file_mock(name="testi1.xml"))
        cls.form_2.instances.create(
            file=cls.create_file_mock(name="testi2.xml"), device=m.Device.objects.create(test_device=True)
        )
        cls.form_2.save()

        cls.project_1.unit_types.add(cls.jedi_council)
        cls.project_1.unit_types.add(cls.jedi_academy)
        cls.project_1.forms.add(cls.form_1)
        cls.project_1.forms.add(cls.form_2)
        cls.project_1.save()

    def test_forms_list_without_auth(self):
        """GET /forms/ without auth: 0 result"""

        response = self.client.get("/api/forms/")
        self.assertJSONResponse(response, 200)

        self.assertValidFormListData(response.json(), 0)

    def test_forms_list_without_auth_for_project_requiring_auth(self):
        """GET /forms/ without auth for project which requires it: 401"""

        response = self.client.get("/api/forms/", {APP_ID: self.project_1.app_id})
        self.assertJSONResponse(response, 401)

    def test_forms_list_with_wrong_auth_for_project_requiring_auth(self):
        """GET /forms/ with wrong auth for project which requires it: 401"""

        self.client.force_authenticate(user=self.iron_man)
        response = self.client.get("/api/forms/", {APP_ID: self.project_1.app_id})
        self.assertJSONResponse(response, 401)

    def test_forms_list_with_auth_for_project_requiring_auth(self):
        """GET /forms/ with auth for project which requires it: 200"""

        self.client.force_authenticate(user=self.yoda)
        response = self.client.get("/api/forms/", {APP_ID: self.project_1.app_id})
        self.assertJSONResponse(response, 200)

    def test_forms_list_empty_for_user(self):
        """GET /forms/ with a user that has no access to any form"""

        self.client.force_authenticate(self.raccoon)
        response = self.client.get("/api/forms/")
        self.assertJSONResponse(response, 200)

        self.assertValidFormListData(response.json(), 0)

    def test_forms_list_ok(self):
        """GET /forms/ web app happy path: we expect two results"""

        self.client.force_authenticate(self.yoda)
        response = self.client.get("/api/forms/", headers={"Content-Type": "application/json"})
        self.assertJSONResponse(response, 200)
        self.assertValidFormListData(response.json(), 2)

    def find_forms_data_for(self, response, form):
        return [f for f in response.json()["forms"] if f["name"] == form.name][0]

    def test_forms_list_ok_has_mappings_true(self):
        """GET /forms/ web app happy path: we expect two results one with has_mappings"""

        mapping = Mapping(form=self.form_2, data_source=self.sw_source, mapping_type=AGGREGATE)
        mapping.save()

        self.client.force_authenticate(self.yoda)
        response = self.client.get("/api/forms/", headers={"Content-Type": "application/json"})
        self.assertJSONResponse(response, 200)
        self.assertValidFormListData(response.json(), 2)

        self.assertTrue(self.find_forms_data_for(response, self.form_2)["has_mappings"])
        self.assertFalse(self.find_forms_data_for(response, self.form_1)["has_mappings"])

    def test_forms_list_filtered_by_org_unit_type(self):
        self.client.force_authenticate(self.yoda)
        # Filter by org_unit type `jedi_council` and `jedi_academy`.
        response = self.client.get(
            f"/api/forms/?orgUnitTypeIds={self.jedi_council.pk}&{self.jedi_academy.pk}",
            headers={"Content-Type": "application/json"},
        )
        self.assertJSONResponse(response, 200)
        self.assertValidFormListData(response.json(), 1)
        # Filter by org_unit type `sith_guild`.
        response = self.client.get(
            f"/api/forms/?orgUnitTypeIds={self.sith_guild.pk}",
            headers={"Content-Type": "application/json"},
        )
        self.assertJSONResponse(response, 200)
        self.assertValidFormListData(response.json(), 0)

    def test_forms_list_filtered_by_project(self):
        """GET /forms/ filtered by project"""
        self.client.force_authenticate(self.yoda)
        # Filter by project 1 and 2.
        response = self.client.get(
            f"/api/forms/?projectsIds={self.project_1.pk}&{self.project_2.pk}",
            headers={"Content-Type": "application/json"},
        )
        self.assertJSONResponse(response, 200)
        self.assertValidFormListData(response.json(), 2)
        # Filter by project 2 only.
        response = self.client.get(
            f"/api/forms/?projectsIds={self.project_2.pk}", headers={"Content-Type": "application/json"}
        )
        self.assertJSONResponse(response, 200)
        self.assertValidFormListData(response.json(), 0)

    def test_form_return_only_deleted(self):
        """GET /forms/ return only deleted forms"""
        self.client.force_authenticate(self.yoda)
        self.client.post(
            f"/api/forms/",
            data={
                "name": "test form 1",
                "period_type": "MONTH",
                "project_ids": [self.project_1.id],
                "org_unit_type_ids": [self.jedi_council.id, self.jedi_academy.id],
            },
            format="json",
        )

        self.client.post(
            f"/api/forms/",
            data={
                "name": "test form 2",
                "period_type": "MONTH",
                "project_ids": [self.project_1.id],
                "org_unit_type_ids": [self.jedi_council.id, self.jedi_academy.id],
            },
            format="json",
        )

        form_to_delete = Form.objects.last()
        form_to_delete.delete()

        response = self.client.get(
            "/api/forms/?&order=instance_updated_at&page=1&showDeleted=true&searchActive=true&all=true&limit=50&undefined=true",
            headers={"Content-Type": "application/json"},
        )

        self.assertJSONResponse(response, 200)
        self.assertEqual(response.json()["count"], 1)

    def test_forms_list_ok_hide_derived_forms(self):
        """GET /forms/ web app happy path: we expect 1 results if one of the form is marked as derived"""
        self.client.force_authenticate(self.yoda)
        response = self.client.get(f"/api/forms/?app_id={self.project_1.app_id}")
        self.assertJSONResponse(response, 200)
        self.assertValidFormListData(response.json(), 2)

        self.form_2.derived = True
        self.form_2.save()

        response = self.client.get(f"/api/forms/?app_id={self.project_1.app_id}")
        self.assertJSONResponse(response, 200)
        self.assertValidFormListData(response.json(), 1)

    def test_forms_list_date_to_inclusive(self):
        """GET /forms/ web app happy path: to_date should be inclusive"""

        date_to = self.now.strftime("%Y-%m-%d")
        self.client.force_authenticate(self.yoda)
        response = self.client.get(f"/api/forms/?date_to={date_to}", headers={"Content-Type": "application/json"})
        self.assertJSONResponse(response, 200)
        self.assertValidFormListData(response.json(), 2)

    def test_forms_list_paginated(self):
        """GET /forms/ paginated happy path"""

        self.client.force_authenticate(self.yoda)
        response = self.client.get("/api/forms/?limit=1&page=1", headers={"Content-Type": "application/json"})
        self.assertJSONResponse(response, 200)

        response_data = response.json()
        self.assertValidFormListData(response_data, 1, True)
        self.assertEqual(response_data["page"], 1)
        self.assertEqual(response_data["pages"], 2)
        self.assertEqual(response_data["limit"], 1)
        self.assertEqual(response_data["count"], 2)

    def test_forms_list_csv_with_flag(self):
        """GET /forms/ csv happy path"""

        self.client.force_authenticate(self.yoda)
        response = self.client.get("/api/forms/?csv=1", headers={"Content-Type": "application/json"})
        self.assertFileResponse(response, 200, "text/csv", expected_attachment_filename="forms.csv", streaming=True)

    def test_forms_list_csv_using_header(self):
        """GET /forms/ csv happy path"""

        self.client.force_authenticate(self.yoda)
        response = self.client.get("/api/forms/?format=csv", headers={"Content-Type": "text/csv"})
        self.assertFileResponse(response, 200, "text/csv; charset=utf-8")

    def test_forms_list_xslx(self):
        """GET /forms/ xslx happy path"""

        self.client.force_authenticate(self.yoda)
        response = self.client.get("/api/forms/?xlsx=1", headers={"Content-Type": "application/json"})
        self.assertFileResponse(
            response,
            200,
            CONTENT_TYPE_XLSX,
            expected_attachment_filename="forms.xlsx",
        )

    def test_forms_retrieve_without_auth(self):
        """GET /forms/<form_id> without auth should result in a 404"""

        response = self.client.get(f"/api/forms/{self.form_1.id}/")
        self.assertJSONResponse(response, 404)

    def test_forms_retrieve_wrong_auth(self):
        """GET /forms/<form_id> with auth of unrelated user should result in a 404"""

        self.client.force_authenticate(self.raccoon)
        response = self.client.get(f"/api/forms/{self.form_1.id}/")
        self.assertJSONResponse(response, 404)

    def test_forms_retrieve_not_found(self):
        """GET /forms/<form_id>: id does not exist"""

        self.client.force_authenticate(self.yoda)
        response = self.client.get(f"/api/forms/292003030/")
        self.assertJSONResponse(response, 404)

    def test_forms_retrieve_ok_1(self):
        """GET /forms/<form_id> happy path (simple form)"""

        self.client.force_authenticate(self.yoda)
        response = self.client.get(f"/api/forms/{self.form_1.id}/")
        self.assertJSONResponse(response, 200)
        self.assertValidFormData(response.json())

    def test_forms_retrieve_ok_2(self):
        """GET /forms/<form_id> happy path (more complex form, additional fields)"""

        self.client.force_authenticate(self.yoda)
        response = self.client.get(f"/api/forms/{self.form_2.id}/")
        self.assertJSONResponse(response, 200)

        form_data = response.json()
        self.assertValidFullFormData(form_data)
        self.assertEqual(1, form_data["instances_count"])

    def test_forms_create_ok(self):
        """POST /forms/ happy path"""

        self.client.force_authenticate(self.yoda)
        response = self.client.post(
            f"/api/forms/",
            data={
                "name": "test form 1",
                "period_type": "MONTH",
                "periods_before_allowed": 1,
                "periods_after_allowed": 0,
                "project_ids": [self.project_1.id],
                "org_unit_type_ids": [self.jedi_council.id, self.jedi_academy.id],
            },
            format="json",
        )
        self.assertJSONResponse(response, 201)

        response_data = response.json()
        self.assertValidFormData(response_data)
        form = m.Form.objects.get(pk=response_data["id"])
        self.assertEqual(1, form.projects.count())
        self.assertEqual(2, form.org_unit_types.count())

    def test_forms_create_ok_without_period_type(self):
        """POST /forms/ happy path without period type"""

        self.client.force_authenticate(self.yoda)
        response = self.client.post(
            f"/api/forms/",
            data={
                "name": "test form 1",
                "period_type": None,
                "periods_before_allowed": 0,
                "periods_after_allowed": 0,
                "project_ids": [self.project_1.id],
                "org_unit_type_ids": [self.jedi_council.id, self.jedi_academy.id],
            },
            format="json",
        )
        self.assertJSONResponse(response, 201)

        response_data = response.json()
        self.assertValidFormData(response_data)
        form = m.Form.objects.get(pk=response_data["id"])
        self.assertEqual(1, form.projects.count())
        self.assertEqual(2, form.org_unit_types.count())

    def test_forms_create_not_ok_with_period_type_and_wrong_period_before_and_after(self):
        """POST /forms/ with wrong period before and after"""

        self.client.force_authenticate(self.yoda)
        response = self.client.post(
            f"/api/forms/",
            data={
                "name": "test form 1",
                "period_type": "MONTH",
                "periods_before_allowed": 0,
                "periods_after_allowed": 0,
                "project_ids": [self.project_1.id],
                "org_unit_type_ids": [self.jedi_council.id, self.jedi_academy.id],
            },
            format="json",
        )
        self.assertJSONResponse(response, 400)

        response_data = response.json()
        self.assertEqual(
            response_data["periods_allowed"][0],
            "periods_before_allowed + periods_after_allowed should be greater than or equal to 1",
        )

    def test_forms_create_ok_extended(self):
        """POST /forms/ happy path (more fields)"""

        self.client.force_authenticate(self.yoda)
        response = self.client.post(
            f"/api/forms/",
            data={
                "name": "test form 2",
                "period_type": "QUARTER",
                "device_field": "deviceid",
                "location_field": "position",
                "single_per_period": True,
                "periods_before_allowed": 2,
                "periods_after_allowed": 10,
                "project_ids": [self.project_1.id],
                "org_unit_type_ids": [self.jedi_council.id, self.jedi_academy.id],
            },
            format="json",
        )
        self.assertJSONResponse(response, 201)

        response_data = response.json()
        self.assertValidFormData(response_data)
        self.assertHasField(response_data, "location_field", str)
        self.assertHasField(response_data, "device_field", str)
        self.assertEqual(response_data["periods_before_allowed"], 2)
        self.assertEqual(response_data["periods_after_allowed"], 10)

    def test_forms_create_without_auth(self):
        """POST /forms/ without auth: 401"""

        response = self.client.post(f"/api/forms/", data={"name": "test form"}, format="json")
        self.assertJSONResponse(response, 401)

    def test_forms_create_wrong_permission(self):
        """POST /forms/ with auth but not the proper permission: 403"""

        self.client.force_authenticate(self.iron_man)
        response = self.client.post(f"/api/forms/", data={"name": "test form"}, format="json")
        self.assertJSONResponse(response, 403)

    def test_forms_create_invalid_1(self):
        """POST /forms/ with a lot of missing/invalid data"""

        self.client.force_authenticate(self.yoda)
        response = self.client.post(
            f"/api/forms/", data={"period_type": "LOL", "single_per_period": "Oui"}, format="json"
        )
        self.assertJSONResponse(response, 400)

        response_data = response.json()
        self.assertHasError(response.json(), "name")
        self.assertHasError(response_data, "period_type")
        self.assertHasError(response_data, "single_per_period")
        self.assertHasError(response_data, "project_ids")
        self.assertHasError(response_data, "org_unit_type_ids")

    def test_forms_create_invalid_2(self):
        """POST /forms/ specific check for allow_empty"""

        self.client.force_authenticate(self.yoda)
        response = self.client.post(f"/api/forms/", data={"project_ids": []}, format="json")
        self.assertJSONResponse(response, 400)

        response_data = response.json()
        self.assertHasError(response_data, "project_ids")

    def test_forms_create_invalid_3(self):
        """POST /forms/ with wrong values for None period type"""

        self.client.force_authenticate(self.yoda)
        response = self.client.post(
            f"/api/forms/",
            data={
                "name": "test form 2",
                "period_type": None,
                "single_per_period": True,
                "periods_before_allowed": 3,
                "periods_after_allowed": 3,
                "project_ids": [self.project_1.id],
                "org_unit_type_ids": [self.jedi_council.id, self.jedi_academy.id],
            },
            format="json",
        )
        self.assertJSONResponse(response, 400)

        response_data = response.json()
        self.assertHasError(response_data, "periods_before_allowed")
        self.assertHasError(response_data, "periods_after_allowed")

    def test_forms_create_wrong_project(self):
        """POST /forms/ - user has no access to the project"""

        self.client.force_authenticate(self.raccoon)
        response = self.client.post(
            f"/api/forms/",
            data={
                "name": "test form",
                "form_id": "test_001",
                "period_type": "MONTH",
                "single_per_period": False,
                "project_ids": [self.project_1.id],
                "org_unit_type_ids": [self.jedi_council.id],
            },
            format="json",
        )
        self.assertJSONResponse(response, 400)
        self.assertHasError(response.json(), "project_ids", "Invalid project ids")

    def test_forms_create_wrong_org_unit_types(self):
        """POST /forms/ - mismatch between project and org unit types"""

        self.client.force_authenticate(self.yoda)
        response = self.client.post(
            f"/api/forms/",
            data={
                "name": "another test form",
                "form_id": "test_002",
                "period_type": "MONTH",
                "single_per_period": False,
                "project_ids": [self.project_1.id],
                "org_unit_type_ids": [self.sith_guild.id],
            },
            format="json",
        )
        self.assertJSONResponse(response, 400)
        self.assertHasError(response.json(), "org_unit_type_ids", "Invalid org unit type ids")

    def test_forms_update_ok(self):
        """PUT /forms/<form_id>: happy path (validation is already covered by create tests)"""

        """POST /forms/ happy path"""

        self.client.force_authenticate(self.yoda)
        response = self.client.put(
            f"/api/forms/{self.form_1.id}/",
            data={
                "name": "test form 1 (updated)",
                "period_type": "QUARTER",
                "pperiods_before_allowed": "0",
                "periods_after_allowed": "1",
                "single_per_period": True,
                "device_field": "deviceid",
                "location_field": "location",
                "project_ids": [self.project_1.id, self.project_2.id],
                "org_unit_type_ids": [self.jedi_council.id],
            },
            format="json",
        )
        self.assertJSONResponse(response, 200)

        response_data = response.json()
        self.assertValidFormData(response_data)
        self.assertEqual(response_data["name"], "test form 1 (updated)")
        self.assertEqual(response_data["period_type"], "QUARTER")
        self.assertTrue(response_data["single_per_period"])
        self.assertEqual(response_data["device_field"], "deviceid")
        self.assertEqual(response_data["location_field"], "location")

        form = m.Form.objects.get(pk=response_data["id"])
        self.assertEqual(2, form.projects.count())
        self.assertEqual(1, form.org_unit_types.count())

    def test_forms_destroy_ok(self):
        """DELETE /forms/<form_id> happy path"""

        self.client.force_authenticate(self.yoda)
        response = self.client.delete(f"/api/forms/{self.form_1.id}/", format="json")
        self.assertJSONResponse(response, 204)

        self.assertIsNotNone(Form.objects_only_deleted.get(pk=self.form_1.id))
        self.assertFalse(Form.objects.filter(pk=self.form_1.id).exists())

    def test_forms_destroy_with_instances(self):
        """DELETE /forms/<form_id> form has instance: cannot be deleted"""

        self.client.force_authenticate(self.yoda)
        response = self.client.delete(f"/api/forms/{self.form_2.id}/", format="json")
        self.assertJSONResponse(response, 204)

    def test_forms_can_restore_deleted_form(self):
        """PATCH /forms/<form_id>/?only_deleted=1"""
        self.form_1.delete()

        self.assertIsNotNone(Form.objects_only_deleted.get(pk=self.form_1.id))
        self.assertFalse(Form.objects.filter(pk=self.form_1.id).exists())

        self.client.force_authenticate(self.yoda)
        response = self.client.patch(
            f"/api/forms/{self.form_1.id}/?only_deleted=1",
            format="json",
            headers={"accept": "application/json"},
            data={
                "deleted_at": None,
            },
        )

        self.assertJSONResponse(response, 200)

        self.assertIsNotNone(Form.objects.get(pk=self.form_1.id))
        self.assertFalse(Form.objects_only_deleted.filter(pk=self.form_1.id).exists())

    def test_forms_destroy_wrong_auth(self):
        """DELETE /forms/<form_id> with user that cannot access form -> 404"""

        self.client.force_authenticate(self.raccoon)
        response = self.client.delete(f"/api/forms/{self.form_1.id}/", format="json")
        self.assertJSONResponse(response, 404)

    def test_forms_destroy_no_auth(self):
        """DELETE /forms/<form_id> without auth -> 401"""

        response = self.client.delete(f"/api/forms/{self.form_1.id}/", format="json")
        self.assertJSONResponse(response, 401)

    # noinspection DuplicatedCode
    def assertValidFormListData(self, list_data: typing.Mapping, expected_length: int, paginated: bool = False):
        self.assertValidListData(
            list_data=list_data, expected_length=expected_length, results_key="forms", paginated=paginated
        )

        for form_data in list_data["forms"]:
            self.assertValidFormData(form_data)

    # noinspection DuplicatedCode
    def assertValidFormData(self, form_data: typing.Mapping):
        self.assertHasField(form_data, "id", int)
        self.assertHasField(form_data, "name", str)
        self.assertHasField(form_data, "periods_before_allowed", int)
        self.assertHasField(form_data, "periods_after_allowed", int)
        self.assertHasField(form_data, "created_at", float)
        self.assertHasField(form_data, "updated_at", float)

    # noinspection DuplicatedCode
    def assertValidFullFormData(self, form_data: typing.Mapping):
        self.assertValidFormData(form_data)

        self.assertHasField(form_data, "device_field", str)
        self.assertHasField(form_data, "location_field", str)
        self.assertHasField(form_data, "form_id", str)
        self.assertHasField(form_data, "period_type", str)
        self.assertHasField(form_data, "single_per_period", bool)
        self.assertHasField(form_data, "org_unit_types", list)
        self.assertHasField(form_data, "projects", list)
        self.assertHasField(form_data, "instances_count", int)
        self.assertHasField(form_data, "instance_updated_at", float)

        for org_unit_type_data in form_data["org_unit_types"]:
            self.assertIsInstance(org_unit_type_data, dict)
            self.assertHasField(org_unit_type_data, "id", int)

        for project_data in form_data["projects"]:
            self.assertIsInstance(project_data, dict)
            self.assertHasField(project_data, "id", int)

        self.assertHasField(form_data, "instance_updated_at", float)
        self.assertHasField(form_data, "instances_count", int)
        self.assertHasField(form_data, "latest_form_version", dict)
        self.assertHasField(form_data["latest_form_version"], "id", int)
        self.assertHasField(form_data["latest_form_version"], "version_id", str)
        self.assertHasField(form_data["latest_form_version"], "file", str)
        self.assertHasField(form_data["latest_form_version"], "created_at", float)
        self.assertHasField(form_data["latest_form_version"], "updated_at", float)

    def test_forms_list_planning(self):
        """GET /forms/ web app happy path: we expect two results"""

        self.client.force_authenticate(self.yoda)
        response = self.client.get("/api/forms/", headers={"Content-Type": "application/json"})
        self.assertJSONResponse(response, 200)
        self.assertValidFormListData(response.json(), 2)

        form_1 = self.form_1
        form_2 = self.form_2
        orgunit_1 = m.OrgUnit.objects.create(name="Org Unit 1")
        team1 = m.Team.objects.create(project=self.project_1, name="team1", manager=self.yoda)
        planning_1 = m.Planning.objects.create(
            name="Planning 1", org_unit=orgunit_1, project=self.project_1, team=team1
        )
        planning_2 = m.Planning.objects.create(
            name="Planning 2", org_unit=orgunit_1, project=self.project_2, team=team1
        )

        planning_1.forms.add(form_1)

        # it should return only form_1
        self.client.force_authenticate(self.yoda)
        response = self.client.get(
            "/api/forms/", {"planning": planning_1.id}, headers={"Content-Type": "application/json"}
        )
        self.assertJSONResponse(response, 200)
        self.assertValidFormListData(response.json(), 1)
        self.assertEqual(response.json()["forms"][0]["name"], form_1.name)

        # it should return form_1 and form_2
        self.client.force_authenticate(self.yoda)
        response = self.client.get("/api/forms/", headers={"Content-Type": "application/json"})
        self.assertJSONResponse(response, 200)
        self.assertValidFormListData(response.json(), 2)
        self.assertEqual(response.json()["forms"][0]["name"], form_2.name)
        self.assertEqual(response.json()["forms"][1]["name"], form_1.name)

        # it should return none of the forms
        self.client.force_authenticate(self.yoda)
        response = self.client.get(
            "/api/forms/", {"planning": planning_2.id}, headers={"Content-Type": "application/json"}
        )
        self.assertJSONResponse(response, 200)
        self.assertValidFormListData(response.json(), 0)

    def test_instance_not_in_same_project_are_not_counted(self):
        """
        This test ensure that the instance count on list form is not multiplied by the number of projects with
        instances linked to the same form.
        """

        self.client.force_authenticate(self.yoda)
        self.yoda.iaso_profile.org_units.set(OrgUnit.objects.all())

        response = self.client.get("/api/forms/", headers={"Content-Type": "application/json"})

        self.assertJSONResponse(response, 200)
        self.assertValidFormListData(response.json(), 2)
        self.assertEqual(0, response.json()["forms"][1]["instances_count"])

        with open("iaso/tests/fixtures/hydroponics_test_upload.xml") as instance_file:
            instance_1 = Instance.objects.create(
                form=self.form_2,
                period="202001",
                org_unit=self.jedi_council_corruscant,
                project=self.project_2,
            )
            instance_1.file.save("hydroponics_test_upload.xml", File(instance_file))
            instance_2 = Instance.objects.create(
                form=self.form_2,
                period="202001",
                org_unit=self.jedi_council_corruscant,
                project=self.project_3,
            )
            instance_2.file.save("hydroponics_test_upload.xml", File(instance_file))

        response = self.client.get("/api/forms/", headers={"Content-Type": "application/json"})

        self.assertJSONResponse(response, 200)
        self.assertValidFormListData(response.json(), 2)
        self.assertEqual(response.json()["forms"][0]["instances_count"], 2)
