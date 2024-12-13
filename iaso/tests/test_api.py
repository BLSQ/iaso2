import json
import typing
from math import floor

from rest_framework.test import APIClient

from ..models import OrgUnit, Form, Instance, OrgUnitType, Account, Project, SourceVersion, DataSource
from ..test import APITestCase


class BasicAPITestCase(APITestCase):
    def setUp(self):
        source = DataSource.objects.create(name="Source")
        old_version = SourceVersion.objects.create(number=1, data_source=source)
        default_version = SourceVersion.objects.create(number=2, data_source=source)

        account = Account(name="Les Inconnus", default_version=default_version)
        account.save()

        self.project = Project(name="Le spectacle", app_id="org.inconnus.spectacle", account=account)
        self.project.save()

        unit_type = OrgUnitType(name="Hospital", short_name="Hosp")
        unit_type.save()
        self.project.unit_types.add(unit_type)

        unit_type_2 = OrgUnitType(name="CDS", short_name="CDS")
        unit_type_2.save()

        self.project.unit_types.add(unit_type_2)
        unit_type.sub_unit_types.add(unit_type_2)

        OrgUnit.objects.create(version=old_version, name="Odd org unit", org_unit_type=unit_type)

        self.form_1 = Form.objects.create(name="Hydroponics study")
        self.form_2 = Form.objects.create(name="Another hydroponics study")
        self.project.forms.add(self.form_1)
        self.project.forms.add(self.form_2)

    def test_org_unit_insertion(self):
        """Creating Org Units through the API"""

        c = APIClient()
        hospital_unit_type = OrgUnitType.objects.get(name="Hospital")
        uuid = "f6ec1672-ab58-4fb2-a4a0-4af80573e2ae"
        name = "Hopital Velpo"

        # with latitude and longitude
        unit_body = [
            {
                "id": uuid,
                "latitude": 50.503,
                "created_at": 1565194077692,
                "updated_at": 1565194077693,
                "orgUnitTypeId": hospital_unit_type.id,
                "parentId": None,
                "longitude": 4.469,
                "altitude": 110,
                "accuracy": 0,
                "time": 0,
                "name": name,
            }
        ]

        response = c.post("/api/orgunits/?app_id=org.inconnus.spectacle", data=unit_body, format="json")
        self.assertEqual(response.status_code, 200)
        velpo_model = OrgUnit.objects.get(uuid=uuid)
        self.assertEqual(velpo_model.name, name)
        # Location should be filled
        self.assertEqual(4.469, velpo_model.location.x)
        self.assertEqual(50.503, velpo_model.location.y)
        self.assertEqual(110, velpo_model.location.z)

        # make sure APIImport record has been created
        self.assertAPIImport("orgUnit", request_body=unit_body, has_problems=False)

        response = c.get("/api/orgunits/?app_id=org.inconnus.spectacle", accept="application/json")

        json_response = json.loads(response.content)

        units = json_response["orgUnits"]
        self.assertEqual(len(units), 0)

        velpo_model.validation_status = OrgUnit.VALIDATION_VALID
        velpo_model.save()

        response = c.get("/api/orgunits/?app_id=org.inconnus.spectacle", accept="application/json")

        content_1 = response.content
        json_response = json.loads(response.content)

        units = json_response["orgUnits"]
        self.assertEqual(1, len(units))  # two org units but only one for default version
        velpo_json = units[0]
        self.assertEqual(velpo_json["name"], name)
        self.assertEqual(floor(velpo_json["created_at"]), floor(1565194077692 / 1000))
        self.assertTrue(floor(velpo_json["updated_at"]) > floor(1565194077693 / 1000))
        self.assertEqual(velpo_json["org_unit_type_id"], hospital_unit_type.id)
        self.assertEqual(velpo_json["parent_id"], None)
        self.assertEqual(velpo_json["latitude"], 50.503)
        self.assertEqual(velpo_json["longitude"], 4.469)
        self.assertEqual(velpo_json["altitude"], 110)
        self.assertEqual(velpo_json["id"], velpo_model.id)

        response = c.get(
            "/api/orgunits/?app_id=org.inconnus.spectacle", accept="application/json"
        )  # this should be the same result as without the app_id
        content_2 = response.content
        self.assertEqual(content_1, content_2)

        response = c.get(
            "/api/orgunits/?app_id=com.pascallegitimus.iaso", accept="application/json"
        )  # this should have 0 result
        json_response = json.loads(response.content)
        self.assertEqual(len(json_response["orgUnits"]), 0)

        # inserting a child org_unit
        uuid2 = "61e1dbfe-a1fc-4075-bfa2-5f3201c918f1"
        name2 = "Hopital Sous Fifre"

        # without latitude / longitude (our code handles lat=0, lng=0 as "no location provided")
        unit_body_2 = {
            "id": uuid2,
            "latitude": 0,
            "created_at": 1565194077699,
            "updated_at": 1565194077800,
            "orgUnitTypeId": hospital_unit_type.id,
            "parentId": uuid,
            "longitude": 0,
            "altitude": 0,
            "accuracy": 0,
            "time": 0,
            "name": name2,
        }

        response = c.post("/api/orgunits/?app_id=org.inconnus.spectacle", data=[unit_body_2], format="json")
        self.assertEqual(response.status_code, 200)

        fifre_model = OrgUnit.objects.get(uuid=uuid2)
        self.assertEqual(fifre_model.name, name2)
        # No location field should be filled

        self.assertIsNone(fifre_model.location)

    def test_org_unit_insertion_new_field_names(self):
        """Creating Org Units through the API but using org_unit_type_id and parent_id instead of orgUnitTypeId and parentId"""
        c = APIClient()
        hospital_unit_type = OrgUnitType.objects.get(name="Hospital")
        uuid = "w5dg2671-aa59-4fb2-a4a0-4af80573e2de"
        name = "Hopital Saint-André"
        unit_body = [
            {
                "id": uuid,
                "latitude": 0,
                "created_at": 1565194077692,
                "updated_at": 1565194077693,
                "org_unit_type_id": hospital_unit_type.id,
                "parent_id": None,
                "longitude": 0,
                "accuracy": 0,
                "time": 0,
                "name": name,
            }
        ]

        response = c.post("/api/orgunits/?app_id=org.inconnus.spectacle", data=unit_body, format="json")
        self.assertEqual(response.status_code, 200)
        velpo_model = OrgUnit.objects.get(uuid=uuid)
        self.assertEqual(velpo_model.name, name)

        response = c.get("/api/orgunits/?app_id=org.inconnus.spectacle", accept="application/json")

        json_response = json.loads(response.content)

        units = json_response["orgUnits"]
        self.assertEqual(len(units), 0)

        velpo_model.validation_status = OrgUnit.VALIDATION_VALID
        velpo_model.save()

        response = c.get("/api/orgunits/?app_id=org.inconnus.spectacle", accept="application/json")

        content_1 = response.content
        json_response = json.loads(response.content)

        units = json_response["orgUnits"]
        velpo_json = units[0]
        self.assertEqual(velpo_json["name"], name)
        self.assertEqual(floor(velpo_json["created_at"]), floor(1565194077692 / 1000))
        self.assertTrue(floor(velpo_json["updated_at"]) > floor(1565194077693 / 1000))
        self.assertEqual(velpo_json["org_unit_type_id"], hospital_unit_type.id)
        self.assertEqual(velpo_json["parent_id"], None)
        self.assertIsNone(velpo_json["latitude"])
        self.assertIsNone(velpo_json["longitude"])
        self.assertIsNone(velpo_json["altitude"])
        self.assertEqual(velpo_json["id"], velpo_model.id)

        response = c.get(
            "/api/orgunits/?app_id=org.inconnus.spectacle", accept="application/json"
        )  # this should be the same result as without the app_id
        content_2 = response.content
        self.assertEqual(content_1, content_2)

        response = c.get(
            "/api/orgunits/?app_id=com.pascallegitimus.iaso", accept="application/json"
        )  # this should have 0 result
        json_response = json.loads(response.content)
        self.assertEqual(len(json_response["orgUnits"]), 0)

        # inserting a child org_unit
        uuid2 = "61e1dbfe-a0fc-4075-bfa2-5f3201c918f3"
        name2 = "Hopital Sous Fifre"
        unit_body_2 = [
            {
                "id": uuid2,
                "latitude": 0,
                "created_at": 1565194077699,
                "updated_at": 1565194077800,
                "orgUnitTypeId": hospital_unit_type.id,
                "parentId": uuid,
                "longitude": 0,
                "accuracy": 0,
                "altitude": 0,
                "time": 0,
                "name": name2,
            }
        ]

        response = c.post("/api/orgunits/?app_id=org.inconnus.spectacle", data=unit_body_2, format="json")
        self.assertEqual(response.status_code, 200)

        fifre_model = OrgUnit.objects.get(uuid=uuid2)
        self.assertEqual(fifre_model.name, name2)

        # No app id - An APIImport record with has_problem set to True should be created
        response = c.post("/api/orgunits/", data=unit_body_2, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertAPIImport(
            "orgUnit",
            request_body=unit_body_2,
            has_problems=True,
            exception_contains_string="Could not find project for user",
        )

        # Wrong app id - An APIImport record with has_problem set to True should be created
        response = c.post("/api/orgunits/?app_id=1234", data=unit_body_2, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertAPIImport(
            "orgUnit",
            request_body=unit_body_2,
            has_problems=True,
            exception_contains_string="Could not find project for user",
        )

    def test_instance_insertion(self):
        """Creating Instance Units through the API"""
        c = APIClient()
        cds_unit_type = OrgUnitType.objects.get(name="CDS")

        uuid = "f6ec1671-aa59-4fb2-a4a0-4af80573e2ae"
        name = "Hopital Velpo"
        unit_body = {
            "id": uuid,
            "latitude": 0,
            "created_at": 1565194077692,
            "updated_at": 1565194077693,
            "orgUnitTypeId": cds_unit_type.id,
            "parentId": None,
            "longitude": 0,
            "accuracy": 0,
            "time": 0,
            "name": name,
        }

        response = c.post("/api/orgunits/?app_id=org.inconnus.spectacle", data=[unit_body], format="json")
        self.assertJSONResponse(response, 200)
        velpo_model = OrgUnit.objects.get(uuid=uuid)
        uuid = "4b7c3954-f69a-4b99-83b1-db73957b32b8"
        name = "Questionnaire CDS"

        form = Form(name="CDS FORM")
        form.save()
        mobile_created_at = 1565258153
        mobile_updated_at = 1565258153
        instance_body = [
            {
                "id": uuid,
                "latitude": 4.4,
                "created_at": mobile_created_at,
                "updated_at": mobile_updated_at,
                "orgUnitId": velpo_model.id,
                "formId": form.id,
                "longitude": 4.4,
                "accuracy": 10,
                "altitude": 100,
                "file": r"\/storage\/emulated\/0\/odk\/instances\/RDC Collecte Data DPS_2_2019-08-08_11-54-46\/RDC Collecte Data DPS_2_2019-08-08_11-54-46.xml",
                "name": name,
            }
        ]

        response = c.post("/api/instances/?app_id=org.inconnus.spectacle", data=instance_body, format="json")
        self.assertEqual(response.status_code, 200)

        instance = Instance.objects.get(uuid=uuid)

        self.assertEqual(instance.name, name)
        self.assertEqual(instance.org_unit_id, velpo_model.id)
        self.assertEqual(instance.form_id, form.id)
        self.assertEqual(instance.location.x, 4.4)
        self.assertEqual(instance.location.y, 4.4)
        self.assertEqual(instance.location.z, 100)
        self.assertEqual(instance.source_created_at.timestamp(), mobile_created_at)
        self.assertEqual(instance.source_updated_at.timestamp(), mobile_updated_at)
        self.assertGreater(instance.created_at, instance.source_created_at)
        self.assertGreater(instance.updated_at, instance.source_updated_at)

        self.assertAPIImport("instance", request_body=instance_body, has_problems=False)

        # No app id - An APIImport record with has_problem set to True should be created
        response = c.post("/api/instances/", data=instance_body, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertAPIImport(
            "instance",
            request_body=instance_body,
            has_problems=True,
            exception_contains_string="Could not find project for user",
        )

        # Wrong app id - An APIImport record with has_problem set to True should be created
        response = c.post("/api/instances/?app_id=9876", data=instance_body, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertAPIImport(
            "instance",
            request_body=instance_body,
            has_problems=True,
            exception_contains_string="Could not find project for user",
        )

    def test_fetch_org_unit_type_v1(self):
        """Fetch Org Unit Types through the API"""
        out = OrgUnitType.objects.get(name="Hospital")
        cds = OrgUnitType.objects.get(name="CDS", short_name="CDS")
        out.allow_creating_sub_unit_types.set([cds])

        out.sub_unit_types.clear()
        out.save()

        c = APIClient()

        response = c.get(
            "/api/orgunittypes/?app_id=com.pascallegitimus.iaso", accept="application/json"
        )  # this should have 0 result
        json_response = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json_response["orgUnitTypes"]), 0)

        response = c.get(
            "/api/orgunittypes/?app_id=org.inconnus.spectacle", accept="application/json"
        )  # this should have 2 results
        json_response = json.loads(response.content)
        org_unit_types = json_response["orgUnitTypes"]
        self.assertEqual(len(org_unit_types), 2)

        found = False
        for org_unit_type_data in org_unit_types:
            self.assertValidOrgUnitTypeData(org_unit_type_data)
            if org_unit_type_data["name"] == "Hospital":
                self.assertLess(org_unit_type_data["created_at"], org_unit_type_data["updated_at"])
                self.assertEqual(len(org_unit_type_data["sub_unit_types"]), 1)
                for sub_org_unit_type_data in org_unit_type_data["sub_unit_types"]:
                    self.assertValidOrgUnitTypeData(sub_org_unit_type_data)
                found = True

        self.assertTrue(found)

    def test_fetch_org_unit_type_v2(self):
        """Fetch Org Unit Types through the API"""
        c = APIClient()

        response = c.get(
            "/api/v2/orgunittypes/?app_id=com.pascallegitimus.iaso", accept="application/json"
        )  # this should have 0 result
        json_response = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json_response["orgUnitTypes"]), 0)

        response = c.get(
            "/api/v2/orgunittypes/?app_id=org.inconnus.spectacle", accept="application/json"
        )  # this should have 2 results
        json_response = json.loads(response.content)
        org_unit_types = json_response["orgUnitTypes"]
        self.assertEqual(len(org_unit_types), 2)

        found = False
        for org_unit_type_data in org_unit_types:
            self.assertValidOrgUnitTypeData(org_unit_type_data)
            if org_unit_type_data["name"] == "Hospital":
                self.assertLess(org_unit_type_data["created_at"], org_unit_type_data["updated_at"])
                self.assertEqual(len(org_unit_type_data["sub_unit_types"]), 1)
                for sub_org_unit_type_data in org_unit_type_data["sub_unit_types"]:
                    self.assertValidOrgUnitTypeData(sub_org_unit_type_data)
                found = True

        self.assertTrue(found)

    def test_forms_list_with_app_id(self):
        """GET /forms/ mobile app happy path (no auth but with app id): 2 results"""

        response = self.client.get(f"/api/forms/?app_id={self.project.app_id}")
        self.assertJSONResponse(response, 200)

        response_data = response.json()
        self.assertValidFormListData(response_data, 2)

        for form_data in response_data["forms"]:
            self.assertValidFormData(form_data)

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

    # noinspection DuplicatedCode
    def assertValidOrgUnitTypeData(self, org_unit_type_data):
        self.assertHasField(org_unit_type_data, "id", int)
        self.assertHasField(org_unit_type_data, "name", str)
        self.assertHasField(org_unit_type_data, "short_name", str)
        self.assertHasField(org_unit_type_data, "depth", int, optional=True)
        self.assertHasField(org_unit_type_data, "sub_unit_types", list, optional=True)
        self.assertHasField(org_unit_type_data, "created_at", float)

        if "sub_unit_types" in org_unit_type_data:
            for sub_org_unit_type_data in org_unit_type_data["sub_unit_types"]:
                self.assertValidOrgUnitTypeData(sub_org_unit_type_data)
