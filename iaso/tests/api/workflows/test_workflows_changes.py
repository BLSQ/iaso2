from rest_framework import status

from iaso.models import WorkflowChange
from iaso.tests.api.workflows.base import BaseWorkflowsAPITestCase

BASE_API = "/api/workflowchanges/"


class WorkflowsChangesAPITestCase(BaseWorkflowsAPITestCase):
    def test_workflow_create_change_without_auth(self):
        response = self.client.post(
            f"{BASE_API}?version_id={self.workflow_version_et_adults_blue.pk}",
            format="json",
            data={"form": self.form_adults_blue.pk, "mapping": {"fake": "data"}},
        )

        self.assertJSONResponse(response, 401)
        self.assertEqual(response.data["detail"].code, "not_authenticated")
        self.assertEqual(response.data["detail"], "Authentication credentials were not provided.")

    def test_workflow_create_change_user_anonymous(self):
        self.client.force_authenticate(self.anon)

        response = self.client.post(
            f"{BASE_API}?version_id={self.workflow_version_et_adults_blue.pk}",
            format="json",
            data={"form": self.form_adults_blue.pk, "mapping": {"fake": "data"}},
        )

        self.assertJSONResponse(response, 403)
        self.assertEqual(response.data["detail"].code, "permission_denied")
        self.assertEqual(
            response.data["detail"],
            "You do not have permission to perform this action.",
        )

    def test_workflow_create_change_with_auth_no_permissions(self):
        self.client.force_authenticate(self.blue_adult_np)

        response = self.client.post(
            f"{BASE_API}?version_id={self.workflow_version_et_adults_blue.pk}",
            format="json",
            data={"form": self.form_adults_blue.pk, "mapping": {"fake": "data"}},
        )

        self.assertJSONResponse(response, 403)
        self.assertEqual(response.data["detail"].code, "permission_denied")
        self.assertEqual(
            response.data["detail"],
            "You do not have permission to perform this action.",
        )

    def test_user_with_auth_no_access_to_reference_form_and_entity_type(self):
        self.client.force_authenticate(self.blue_child_1)

        response = self.client.post(
            f"{BASE_API}?version_id={self.workflow_version_et_children_blue.pk}",
            format="json",
            data={"form": self.form_adults_blue.pk, "mapping": {"fake": "data"}},
        )

        self.assertJSONResponse(response, 400)

    def test_cannot_add_changes_to_version_not_in_draft(self):
        self.client.force_authenticate(self.blue_adult_1)
        response = self.client.post(
            f"{BASE_API}?version_id={self.workflow_version_et_adults_blue.pk}",
            format="json",
            data={"form": self.form_adults_blue.pk, "mapping": {"fake": "data"}},
        )

        self.assertJSONResponse(response, 400)
        assert "is not in draft status" in str(response.data[0])
        assert response.data[0].code == "invalid"

    def test_cannot_add_changes_if_source_form_is_equal_target_form(self):
        # Also checks that it fails if the mapped field does not exist in the source form
        self.client.force_authenticate(self.blue_adult_1)
        response = self.client.post(
            f"{BASE_API}?version_id={self.workflow_version_et_adults_blue_draft.pk}",
            format="json",
            data={"form": self.form_adults_blue.pk, "mapping": {"fake": "data"}},
        )

        self.assertJSONResponse(response, 400)
        assert "Cannot create a WorkflowChange where form and reference form are the same" in str(
            response.data["form"][0]
        )
        assert response.data["form"][0].code == "invalid"

        assert "Question fake does not exist in source form" in str(response.data["mapping"][0])
        assert response.data["mapping"][0].code == "invalid"

    def test_should_field_not_exist_on_reference_form(self):
        self.client.force_authenticate(self.blue_adult_1)
        response = self.client.post(
            f"{BASE_API}?version_id={self.workflow_version_et_adults_blue_draft.pk}",
            format="json",
            data={
                "form": self.form_adults_blue_2.pk,
                "mapping": {"XXXX": "mon_champ"},
            },  # both forms have a mon_champ field
        )

        self.assertJSONResponse(response, 400)
        assert "Question XXXX does not exist in source form" in str(response.data["mapping"][0])
        assert response.data["mapping"][0].code == "invalid"

    def test_delete_non_existing_should_fail(self):
        self.client.force_authenticate(self.blue_adult_1)
        response_delete = self.client.delete("/api/workflowchanges/1000/")
        self.assertContains(
            response_delete, "No WorkflowChange matches the given query", status_code=status.HTTP_404_NOT_FOUND
        )

    def test_create_change_with_non_existing_form_should_fail(self):
        self.client.force_authenticate(self.blue_adult_1)
        response = self.client.post(
            f"{BASE_API}?version_id={self.workflow_version_et_adults_blue_draft.pk}",
            format="json",
            data={"form": 1000, "mapping": {"mon_champ": "mon_champ"}},
        )

        self.assertJSONResponse(response, 400)

    def test_create_update_delete(self):
        self.client.force_authenticate(self.blue_adult_1)
        response = self.client.post(
            f"{BASE_API}?version_id={self.workflow_version_et_adults_blue_draft.pk}",
            format="json",
            data={
                "form": self.form_adults_blue_2.pk,
                "mapping": {"mon_champ": "mon_champ"},
            },  # both forms have a mon_champ field
        )

        created_change = WorkflowChange.objects.get(pk=response.data["id"])

        self.assertJSONResponse(response, 200)
        assert response.data["form"]["id"] == self.form_adults_blue_2.pk
        assert response.data["mapping"] == {"mon_champ": "mon_champ"}

        response_change = self.client.put(
            f"{BASE_API}{created_change.pk}/",
            format="json",
            data={"form": self.form_adults_blue_2.pk, "mapping": {"mon_champ": "mon_champ_2"}},
        )

        self.assertJSONResponse(response_change, 200)
        assert response_change.data["form"] == self.form_adults_blue_2.pk
        assert response_change.data["mapping"] == {"mon_champ": "mon_champ_2"}

        response_delete = self.client.delete(f"{BASE_API}{created_change.pk}/")

        self.assertJSONResponse(response_delete, 204)
        assert response_delete.data is None

    def test_should_fail_field_not_mapped_to_proper_type(self):
        self.client.force_authenticate(self.blue_adult_1)
        response = self.client.post(
            f"{BASE_API}?version_id={self.workflow_version_et_adults_blue_draft.pk}",
            format="json",
            data={
                "form": self.form_adults_blue_2.pk,
                "mapping": {"integer_field": "mon_champ"},
            },  # both forms have a mon_champ field
        )

        self.assertJSONResponse(response, 400)
        assert "Question integer_field and mon_champ do not have the same type" in str(response.data["mapping"][0])
        assert response.data["mapping"][0].code == "invalid"

    def test_should_succeed_calculate_to_any_type(self):
        self.client.force_authenticate(self.blue_adult_1)
        response = self.client.post(
            f"{BASE_API}?version_id={self.workflow_version_et_adults_blue_draft.pk}",
            format="json",
            data={
                "form": self.form_adults_blue_2.pk,
                "mapping": {"calculate_one": "integer_field"},
            },  # both forms have a mon_champ field
        )

        self.assertJSONResponse(response, 200)
        assert response.data["form"]["id"] == self.form_adults_blue_2.pk
        assert response.data["mapping"] == {"calculate_one": "integer_field"}

    def test_should_succeed_any_type_to_calculate(self):
        self.client.force_authenticate(self.blue_adult_1)
        response = self.client.post(
            f"{BASE_API}?version_id={self.workflow_version_et_adults_blue_draft.pk}",
            format="json",
            data={
                "form": self.form_adults_blue_2.pk,
                "mapping": {"integer_field": "calculate_two"},
            },  # both forms have a mon_champ field
        )

        self.assertJSONResponse(response, 200)
        assert response.data["form"]["id"] == self.form_adults_blue_2.pk
        assert response.data["mapping"] == {"integer_field": "calculate_two"}
