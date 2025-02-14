import jsonschema

from iaso.tests.api.workflows.base import BaseWorkflowsAPITestCase

BASE_API = "/api/mobile/workflows/"


class WorkflowsMobileAPITestCase(BaseWorkflowsAPITestCase):
    def test_mobile_api_without_app_id(self):
        self.client.force_authenticate(self.blue_adult_1)

        response = self.client.get(BASE_API)

        self.assertJSONResponse(response, 404)

        assert response.data == "No app_id provided"

    def test_mobile_api_with_nonexisting_app_id(self):
        self.client.force_authenticate(self.blue_adult_1)

        response = self.client.get(f"{BASE_API}?app_id=wrong_app_id")

        self.assertJSONResponse(response, 404)

        assert response.data == "User not found in Projects for this app id or project not found"

    def test_mobile_api_with_nonaccessible_app_id(self):
        self.client.force_authenticate(self.blue_adult_1)

        response = self.client.get(f"{BASE_API}?app_id=red.adults.project")

        self.assertJSONResponse(response, 404)

        assert response.data == "User not found in Projects for this app id or project not found"

    def test_mobile_api_ok(self):
        self.client.force_authenticate(self.blue_adult_1)

        set_tl_schema = {
            "type": "object",
            "properties": {
                "workflows": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "status": {"type": "string"},
                            "created_at": {"type": "number"},
                            "updated_at": {"type": "number"},
                            "version_id": {"type": "number"},
                            "entity_type_id": {"type": "number"},
                            "name": {"type": "string"},
                            "changes": {"type": "array"},
                            "follow_ups": {"type": "array"},
                        },
                    },
                }
            },
            "required": ["workflows"],
        }

        response = self.client.get(f"{BASE_API}?app_id=blue.adults.project")

        self.assertJSONResponse(response, 200)

        try:
            jsonschema.validate(instance=response.data, schema=set_tl_schema)
        except jsonschema.exceptions.ValidationError as ex:
            self.fail(msg=str(ex))

        self.assertEqual(len(response.data["workflows"]), 2)
