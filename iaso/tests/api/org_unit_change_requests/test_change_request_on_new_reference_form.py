from rest_framework.test import APIClient

from iaso.models import OrgUnit, Form, Instance, OrgUnitType, Account, Project, SourceVersion, DataSource
from iaso.models.forms import CR_MODE_IF_REFERENCE_FORM
from iaso.test import APITestCase


class AutoChangeRequestForInstanceFormTestCase(APITestCase):
    def setUp(self):
        source = DataSource.objects.create(name="Source")
        default_version = SourceVersion.objects.create(number=2, data_source=source)

        account = Account(name="Test account", default_version=default_version)
        account.save()

        self.project = Project(name="Test project", app_id="com.example.testproject", account=account)
        self.project.save()

        unit_type = OrgUnitType(name="Hospital", short_name="Hosp")
        unit_type.save()
        self.org_unit_type = unit_type
        self.project.unit_types.add(unit_type)

        self.form_1 = Form.objects.create(name="Form 1", change_request_mode=CR_MODE_IF_REFERENCE_FORM)
        unit_type.reference_forms.add(self.form_1)
        self.project.forms.add(self.form_1)

        self.form_2 = Form.objects.create(name="Form 2")
        unit_type.reference_forms.add(self.form_2)
        self.project.forms.add(self.form_2)

    def test_instance_insertion(self):
        """Creating Instance Units through the API"""
        c = APIClient()

        uuid = "f6ec1671-aa59-4fb2-a4a0-4af80573e2ae"
        name = "An hospital"
        unit_body = {
            "id": uuid,
            "latitude": 0,
            "created_at": 1565194077692,
            "updated_at": 1565194077693,
            "orgUnitTypeId": self.org_unit_type.id,
            "parentId": None,
            "longitude": 0,
            "accuracy": 0,
            "time": 0,
            "name": name,
        }

        response = c.post("/api/orgunits/?app_id=com.example.testproject", data=[unit_body], format="json")
        self.assertJSONResponse(response, 200)
        org_unit_model = OrgUnit.objects.get(uuid=uuid)
        uuid = "4b7c3954-f69a-4b99-83b1-db73957b32b8"
        name = "Questionnaire CDS"

        form = self.form_1
        instance_body = [
            {
                "id": uuid,
                "latitude": 4.4,
                "created_at": 1565258153704,
                "updated_at": 1565258153704,
                "orgUnitId": org_unit_model.id,
                "formId": form.id,
                "longitude": 4.4,
                "accuracy": 10,
                "altitude": 100,
                "file": r"\/storage\/emulated\/0\/odk\/instances\/RDC Collecte Data DPS_2_2019-08-08_11-54-46\/RDC Collecte Data DPS_2_2019-08-08_11-54-46.xml",
                "name": name,
            }
        ]

        response = c.post("/api/instances/?app_id=com.example.testproject", data=instance_body, format="json")
        self.assertEqual(response.status_code, 200)

        instance = Instance.objects.get(uuid=uuid)

        self.assertEqual(instance.orgunitchangerequest_set.count(), 1)

        change_request = instance.orgunitchangerequest_set.first()
        self.assertIsNone(change_request.created_by)
        self.assertEqual(change_request.new_name, "")
        self.assertIsNone(change_request.new_org_unit_type)
        self.assertEqual(change_request.new_groups.count(), 0)
        self.assertIsNone(change_request.new_location)
        self.assertIsNone(change_request.new_location_accuracy)
        self.assertIsNone(change_request.new_opening_date)
        self.assertIsNone(change_request.new_closed_date)
        self.assertEqual(change_request.new_reference_instances.count(), 1)
        self.assertEqual(change_request.requested_fields, ["new_reference_instances"])

        # checking if no change request is created for a form with the option activated
        uuid2 = "4b7c3954-f69a-4b99-83b1-db73957b32b9"

        instance_body = [
            {
                "id": uuid2,
                "latitude": 4.4,
                "created_at": 1565258153704,
                "updated_at": 1565258153704,
                "orgUnitId": org_unit_model.id,
                "formId": self.form_2.id,
                "longitude": 4.4,
                "accuracy": 10,
                "altitude": 100,
                "file": r"\/storage\/emulated\/0\/odk\/instances\/RDC Collecte Data DPS_2_2019-08-08_11-54-46\/RDC Collecte Data DPS_2_2019-08-08_11-54-43.xml",
                "name": name,
            }
        ]

        response = c.post("/api/instances/?app_id=com.example.testproject", data=instance_body, format="json")

        self.assertEqual(response.status_code, 200)

        instance = Instance.objects.get(uuid=uuid2)

        self.assertEqual(len(instance.orgunitchangerequest_set.all()), 0)
