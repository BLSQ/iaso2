import jsonschema

from iaso.models import WorkflowVersion
from iaso.tests.api.workflows.base import BaseWorkflowsAPITestCase

BASE_API = "/api/workflowversions/"

post_answer_schema = {
    "type": "object",
    "properties": {
        "created_at": {"type": "string"},
        "updated_at": {"type": "string"},
        "name": {"type": "string"},
        "status": {"type": "string"},
        "version_id": {"type": "number"},
    },
    "required": ["created_at", "updated_at", "name", "status", "version_id"],
}


class WorkflowsAPITestCase(BaseWorkflowsAPITestCase):
    def test_user_without_auth(self):
        response = self.client.get(f"{BASE_API}?workflow__entity_type={self.et_adults_blue.pk}/")

        self.assertJSONResponse(response, 401)
        self.assertEqual(response.data["detail"].code, "not_authenticated")
        self.assertEqual(response.data["detail"], "Authentication credentials were not provided.")

    def test_user_anonymous(self):
        self.client.force_authenticate(self.anon)
        response = self.client.get(f"{BASE_API}?workflow__entity_type={self.et_adults_blue.pk}/")

        self.assertJSONResponse(response, 403)
        self.assertEqual(response.data["detail"].code, "permission_denied")
        self.assertEqual(
            response.data["detail"],
            "You do not have permission to perform this action.",
        )

    def test_user_with_auth_no_permissions(self):
        self.client.force_authenticate(self.blue_adult_np)

        response = self.client.get(f"{BASE_API}?workflow__entity_type={self.et_children_blue.pk}/")

        self.assertJSONResponse(response, 403)
        self.assertEqual(response.data["detail"].code, "permission_denied")
        self.assertEqual(
            response.data["detail"],
            "You do not have permission to perform this action.",
        )

    def test_user_with_auth_no_access_to_entity_type(self):
        self.client.force_authenticate(self.blue_adult_1)

        # {"workflow__entity_type": ["Select a valid choice. That choice is not one of the available choices."]}
        response = self.client.get(f"{BASE_API}?workflow__entity_type={self.et_children_blue.pk}/")

        self.assertJSONResponse(response, 400)
        assert "workflow__entity_type" in response.data
        assert (
            response.data["workflow__entity_type"][0]
            == "Select a valid choice. That choice is not one of the available choices."
        )

    def test_user_all_access_ok(self):
        self.client.force_authenticate(self.blue_adult_1)

        set_tl_schema = {
            "type": "object",
            "properties": {
                "count": {"type": "number"},
                "has_next": {"type": "boolean"},
                "has_previous": {"type": "boolean"},
                "limit": {"type": "number"},
                "page": {"type": "number"},
                "pages": {"type": "number"},
                "workflow_versions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "status": {"type": "string"},
                            "created_at": {"type": "string"},
                            "updated_at": {"type": "string"},
                            "version_id": {"type": "number"},
                            "name": {"type": "string"},
                        },
                    },
                },
            },
            "required": [
                "count",
                "has_next",
                "has_previous",
                "limit",
                "page",
                "pages",
                "workflow_versions",
            ],
        }

        response = self.client.get(f"{BASE_API}?limit=2")

        self.assertJSONResponse(response, 200)
        self.assertEqual(response.json()["count"], 6)

        try:
            jsonschema.validate(instance=response.data, schema=set_tl_schema)
        except jsonschema.exceptions.ValidationError as ex:
            self.fail(msg=str(ex))

    def test_view_specific_version(self):
        self.client.force_authenticate(self.blue_adult_1)

        set_tl_schema = {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "name": {"type": "string"},
                "updated_at": {"type": "string"},
                "reference_form": {"type": "object"},
                "entity_type": {
                    "type": "object",
                    "properties": {
                        "account": {"type": "number"},
                        "id": {"type": "number"},
                        "name": {"type": "string"},
                    },
                },
                "follow_ups": {"type": "array"},
                "version_id": {"type": "number"},
            },
            "required": [
                "status",
                "name",
                "updated_at",
                "reference_form",
                "entity_type",
                "follow_ups",
                "version_id",
            ],
        }

        response = self.client.get(f"{BASE_API}{self.workflow_version_et_adults_blue.pk}/")

        self.assertJSONResponse(response, 200)

        try:
            jsonschema.validate(instance=response.data, schema=set_tl_schema)
        except jsonschema.exceptions.ValidationError as ex:
            self.fail(msg=str(ex))

    def test_new_version_empty(self):
        self.client.force_authenticate(self.blue_adult_1)

        response = self.client.post(
            f"{BASE_API}",
            format="json",
            data={"entity_type_id": self.et_adults_blue.pk, "name": "New Super Name"},
        )

        self.assertJSONResponse(response, 200)

        try:
            jsonschema.validate(instance=response.data, schema=post_answer_schema)
        except jsonschema.exceptions.ValidationError as ex:
            self.fail(msg=str(ex))

        try:
            w_version = WorkflowVersion.objects.get(pk=response.data["version_id"])

            assert w_version.pk == response.data["version_id"]
            assert w_version.name == "New Super Name"
            assert w_version.reference_form.pk == self.et_adults_blue.reference_form.pk

        except WorkflowVersion.DoesNotExist as ex:
            self.fail(msg=str(ex))

    def test_new_version_from_copy(self):
        self.client.force_authenticate(self.blue_adult_1)

        response = self.client.post(
            f"{BASE_API}{self.workflow_version_et_adults_blue_with_followups_and_changes.pk}/copy/"
        )

        self.assertJSONResponse(response, 200)

        try:
            jsonschema.validate(instance=response.data, schema=post_answer_schema)
        except jsonschema.exceptions.ValidationError as ex:
            self.fail(msg=str(ex))

        try:
            w_version = WorkflowVersion.objects.get(pk=response.data["version_id"])

            assert w_version.pk == response.data["version_id"]
            assert w_version.name == str(
                "Copy of " + self.workflow_version_et_adults_blue_with_followups_and_changes.name
            )

        except WorkflowVersion.DoesNotExist as ex:
            self.fail(msg=str(ex))

    def test_version_search_by_name(self):
        self.client.force_authenticate(self.blue_adult_1)

        response = self.client.get(f"{BASE_API}?search=draft")

        self.assertJSONResponse(response, 200)
        self.assertEqual(len(response.data["workflow_versions"]), 1)

    def test_soft_delete_workflow_version(self):
        self.client.force_authenticate(self.blue_adult_1)

        temp_version = WorkflowVersion.objects.create(
            workflow=self.workflow_et_adults_blue,
            name="workflow_version_et_adults_blue V2",
        )

        response = self.client.delete(f"{BASE_API}{temp_version.id}/")
        self.assertJSONResponse(response, 204)
        loaded_temp_version = WorkflowVersion.objects_include_deleted.get(pk=temp_version.id)

        try:
            WorkflowVersion.objects.get(pk=temp_version.id)
            assert True is False  # We should never reach here
        except WorkflowVersion.DoesNotExist:
            pass

        assert loaded_temp_version.deleted_at is not None
