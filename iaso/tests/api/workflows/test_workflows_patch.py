import jsonschema
from rest_framework import status

from iaso.tests.api.workflows.base import BaseWorkflowsAPITestCase
from iaso.tests.api.workflows.test_workflows import post_answer_schema

BASE_API = "/api/workflowversions/"


class WorkflowsPatchAPITestCase(BaseWorkflowsAPITestCase):
    def test_user_without_auth(self):
        response = self.client.patch(
            f"{BASE_API}{self.workflow_version_et_adults_blue.pk}/",
            data={"status": "PUBLISHED"},
        )

        self.assertJSONResponse(response, 401)
        self.assertEqual(response.data["detail"].code, "not_authenticated")
        self.assertEqual(response.data["detail"], "Authentication credentials were not provided.")

    def test_user_anonymous(self):
        self.client.force_authenticate(self.anon)
        response = self.client.patch(
            f"{BASE_API}{self.workflow_version_et_adults_blue.pk}/",
            data={"status": "PUBLISHED"},
        )

        self.assertJSONResponse(response, 403)
        self.assertEqual(response.data["detail"].code, "permission_denied")
        self.assertEqual(
            response.data["detail"],
            "You do not have permission to perform this action.",
        )

    def test_patch_nonexisting_fails(self):
        self.client.force_authenticate(self.blue_adult_1)

        response = self.client.patch(f"{BASE_API}1000/", data={"status": "PUBLISHED"})
        self.assertContains(
            response, "No WorkflowVersion matches the given query", status_code=status.HTTP_404_NOT_FOUND
        )

    def test_patch_transition_ok(self):
        self.client.force_authenticate(self.blue_adult_1)

        response = self.client.patch(
            f"{BASE_API}{self.workflow_version_et_adults_blue_draft_2.pk}/",
            data={"status": "PUBLISHED"},
        )

        self.assertJSONResponse(response, 200)

        try:
            jsonschema.validate(instance=response.data, schema=post_answer_schema)
        except jsonschema.exceptions.ValidationError as ex:
            self.fail(msg=str(ex))

    def test_patch_transition_forbidden(self):
        self.client.force_authenticate(self.blue_adult_1)

        self.workflow_version_et_adults_blue.status = "PUBLISHED"
        self.workflow_version_et_adults_blue.save()

        response = self.client.patch(
            f"{BASE_API}{self.workflow_version_et_adults_blue.pk}/",
            data={"status": "DRAFT"},
        )

        self.assertJSONResponse(response, 400)

        assert (
            str(response.data)
            == "[ErrorDetail(string='Transition from PUBLISHED to DRAFT is not allowed', code='invalid')]"
        )

    def test_patch_change_name_only(self):
        self.client.force_authenticate(self.blue_adult_1)

        new_name = "BROL"

        response = self.client.patch(
            f"{BASE_API}{self.workflow_version_et_adults_blue.pk}/",
            data={"name": new_name},
        )

        self.assertJSONResponse(response, 200)

        try:
            jsonschema.validate(instance=response.data, schema=post_answer_schema)
        except jsonschema.exceptions.ValidationError as ex:
            self.fail(msg=str(ex))

        assert response.data["name"] == new_name
