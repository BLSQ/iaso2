import datetime
import uuid
import time_machine

from rest_framework import status

from iaso import models as m
from iaso.tests.api.org_unit_change_request_configurations.common_base_with_setup import OUCRCAPIBase


class OrgUnitChangeRequestConfigurationAPITestCase(OUCRCAPIBase):
    """
    Test actions on the OUCRCViewSet.
    """

    DT = datetime.datetime(2023, 10, 17, 17, 0, 0, 0, tzinfo=datetime.timezone.utc)
    OUCRC_API_URL = "/api/orgunits/changes/configs/"

    # *** utility methods for testing ***
    def create_new_org_unit_type(self, new_name=None):
        return m.OrgUnitType.objects.create(name=new_name)

    def make_patch_api_call_with_non_existing_id_in_attribute(self, attribute_name):
        self._make_api_call_with_non_existing_id_in_attribute(attribute_name, "patch")

    def make_post_api_call_with_non_existing_id_in_attribute(self, attribute_name, additional_data={}):
        self._make_api_call_with_non_existing_id_in_attribute(attribute_name, "post", additional_data)

    def _make_api_call_with_non_existing_id_in_attribute(self, attribute_name, method, additional_data={}):
        self.client.force_authenticate(self.user_ash_ketchum)
        probably_not_a_valid_id = 1234567890
        data = {
            **additional_data,
            attribute_name: [probably_not_a_valid_id],
        }

        if method == "post":
            response = self.client.post(f"{self.OUCRC_API_URL}", data=data, format="json")
        elif method == "patch":
            response = self.client.patch(f"{self.OUCRC_API_URL}{self.oucrc_type_fire.id}/", data=data, format="json")
        else:
            raise ValueError("Method must be either 'post' or 'patch'")

        self.assertContains(response, probably_not_a_valid_id, status_code=status.HTTP_400_BAD_REQUEST)

        result = response.json()
        self.assertIn(attribute_name, result)
        self.assertIn(str(probably_not_a_valid_id), result[attribute_name][0])

    # *** Testing list GET endpoint ***
    def test_list_ok(self):
        self.client.force_authenticate(self.user_ash_ketchum)

        # with self.assertNumQueries(12):
        # filter_for_user_and_app_id
        #   1. SELECT OrgUnit
        # get_queryset
        #   2. COUNT(*)
        #   3. SELECT OrgUnitChangeRequest
        # prefetch
        #   4. PREFETCH OrgUnit.groups
        #   5. PREFETCH OrgUnit.reference_instances
        #   6. PREFETCH OrgUnit.reference_instances__form
        #   7. PREFETCH OrgUnitChangeRequest.new_groups
        #   8. PREFETCH OrgUnitChangeRequest.old_groups
        #   9. PREFETCH OrgUnitChangeRequest.new_reference_instances
        #  10. PREFETCH OrgUnitChangeRequest.old_reference_instances
        #  11. PREFETCH OrgUnitChangeRequest.{new/old}_reference_instances__form
        #  12. PREFETCH OrgUnitChangeRequest.org_unit_type.projects
        response = self.client.get(self.OUCRC_API_URL)
        self.assertJSONResponse(response, status.HTTP_200_OK)
        self.assertEqual(3, len(response.data["results"]))

    def test_list_without_auth(self):
        response = self.client.get(self.OUCRC_API_URL)
        self.assertJSONResponse(response, status.HTTP_401_UNAUTHORIZED)

    # list with filters?

    # *** Testing retrieve GET endpoint ***
    def test_retrieve_ok(self):
        self.client.force_authenticate(self.user_misty)
        response = self.client.get(f"{self.OUCRC_API_URL}{self.oucrc_type_water.id}/")
        self.assertJSONResponse(response, status.HTTP_200_OK)

        result = response.data
        self.assertEqual(self.oucrc_type_water.id, result["id"])
        self.assertEqual(str(self.oucrc_type_water.uuid), result["uuid"])
        self.assertEqual(self.oucrc_type_water.project_id, result["project"]["id"])
        self.assertEqual(self.oucrc_type_water.project.name, result["project"]["name"])
        self.assertEqual(self.oucrc_type_water.org_unit_type_id, result["org_unit_type"]["id"])
        self.assertEqual(self.oucrc_type_water.org_unit_type.name, result["org_unit_type"]["name"])
        self.assertEqual(self.oucrc_type_water.org_units_editable, result["org_units_editable"])
        self.assertCountEqual(self.oucrc_type_water.editable_fields, result["editable_fields"])
        self.assertEqual(len(self.oucrc_type_water.possible_types.all()), len(result["possible_types"]))
        self.assertEqual(len(self.oucrc_type_water.possible_parent_types.all()), len(result["possible_parent_types"]))
        self.assertEqual(len(self.oucrc_type_water.group_sets.all()), len(result["group_sets"]))
        self.assertEqual(
            len(self.oucrc_type_water.editable_reference_forms.all()), len(result["editable_reference_forms"])
        )
        self.assertEqual(len(self.oucrc_type_water.group_sets.all()), len(result["group_sets"]))
        self.assertEqual(self.oucrc_type_water.created_by_id, result["created_by"]["id"])
        self.assertIsNone(self.oucrc_type_water.updated_by)
        self.assertEqual(self.oucrc_type_water.created_at.timestamp(), result["created_at"])
        self.assertEqual(self.oucrc_type_water.updated_at.timestamp(), result["updated_at"])

    def test_retrieve_without_auth(self):
        response = self.client.get(f"{self.OUCRC_API_URL}{self.oucrc_type_fire.id}/")
        self.assertJSONResponse(response, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_invalid_id(self):
        probably_not_a_valid_id = 1234567890
        self.client.force_authenticate(self.user_misty)
        response = self.client.get(f"{self.OUCRC_API_URL}{probably_not_a_valid_id}/")
        self.assertJSONResponse(response, status.HTTP_404_NOT_FOUND)

    # *** Testing create POST endpoint ***
    @time_machine.travel(DT, tick=False)
    def test_create_happy_path(self):
        self.client.force_authenticate(self.user_brock)
        random_uuid = uuid.uuid4()
        new_ou_type = self.create_new_org_unit_type("new ou type")
        data = {
            "uuid": random_uuid,
            "project_id": self.project_johto.id,
            "org_unit_type_id": new_ou_type.id,
            "org_units_editable": False,
            "editable_fields": m.OrgUnitChangeRequestConfiguration.LIST_OF_POSSIBLE_EDITABLE_FIELDS,
            "possible_type_ids": [self.ou_type_rock_pokemons.id, self.ou_type_fire_pokemons.id],
            "possible_parent_type_ids": [self.ou_type_rock_pokemons.id, self.ou_type_water_pokemons.id],
            "group_set_ids": [self.group_set_brock_pokemons.id],
            "editable_reference_form_ids": [self.form_rock_throw.id],
            "other_group_ids": [self.other_group_1.id],
        }
        response = self.client.post(self.OUCRC_API_URL, data=data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        oucrc = m.OrgUnitChangeRequestConfiguration.objects.get(uuid=random_uuid)
        self.assertEqual(oucrc.uuid, random_uuid)
        self.assertEqual(oucrc.project.id, self.project_johto.id)
        self.assertEqual(oucrc.org_unit_type_id, new_ou_type.id)
        self.assertEqual(oucrc.org_units_editable, False)
        self.assertCountEqual(oucrc.editable_fields, data["editable_fields"])
        self.assertCountEqual(oucrc.possible_types.values_list("id", flat=True), data["possible_type_ids"])
        self.assertCountEqual(
            oucrc.possible_parent_types.values_list("id", flat=True), data["possible_parent_type_ids"]
        )
        self.assertCountEqual(oucrc.group_sets.values_list("id", flat=True), data["group_set_ids"])
        self.assertCountEqual(
            oucrc.editable_reference_forms.values_list("id", flat=True), data["editable_reference_form_ids"]
        )
        self.assertCountEqual(oucrc.other_groups.values_list("id", flat=True), data["other_group_ids"])
        self.assertEqual(oucrc.created_by_id, self.user_brock.id)
        self.assertEqual(oucrc.created_at, self.DT)
        self.assertIsNone(oucrc.updated_by)
        self.assertEqual(oucrc.updated_at, self.DT)

    # @time_machine.travel(DT, tick=False)
    # def test_create_ok_using_uuid_for_project_id(self):
    #     self.client.force_authenticate(self.user)
    #     data = {
    #         "org_unit_id": self.org_unit.uuid,
    #         "new_name": "I want this new name",
    #         "new_org_unit_type_id": self.org_unit_type.pk,
    #     }
    #     with self.assertNumQueries(11):
    #         response = self.client.post("/api/orgunits/changes/", data=data, format="json")
    #     self.assertEqual(response.status_code, 201)
    #     change_request = m.OrgUnitChangeRequest.objects.get(new_name=data["new_name"])
    #     self.assertEqual(change_request.new_name, data["new_name"])
    #     self.assertEqual(change_request.new_org_unit_type, self.org_unit_type)
    #     self.assertEqual(change_request.created_at, self.DT)
    #     self.assertEqual(change_request.created_by, self.user)
    #     self.assertEqual(change_request.updated_at, self.DT)
    #     self.assertEqual(change_request.requested_fields, ["new_name", "new_org_unit_type"])
    #
    def test_create_without_auth(self):
        random_uuid = uuid.uuid4()
        new_ou_type = self.create_new_org_unit_type("new ou type")
        data = {
            "uuid": random_uuid,
            "project_id": self.project_johto.id,
            "org_unit_type_id": new_ou_type.id,
            "org_units_editable": False,
        }
        response = self.client.post(self.OUCRC_API_URL, data=data, format="json")
        self.assertJSONResponse(response, status.HTTP_401_UNAUTHORIZED)

    #
    # def test_create_without_perm(self):
    #     self.client.force_authenticate(self.user)
    #
    #     unauthorized_org_unit = m.OrgUnit.objects.create()
    #     data = {
    #         "org_unit_id": unauthorized_org_unit.id,
    #         "new_name": "I want this new name",
    #     }
    #     response = self.client.post("/api/orgunits/changes/", data=data, format="json")
    #     self.assertEqual(response.status_code, 403)

    def test_create_existing_invalid_oug_unit_type_and_project(self):
        # an OUCRC already exists with this combination of OUType & Project
        self.client.force_authenticate(self.user_ash_ketchum)
        data = {
            "project_id": self.project_johto.id,
            "org_unit_type_id": self.ou_type_fire_pokemons.id,
            "org_units_editable": False,
        }
        response = self.client.post(self.OUCRC_API_URL, data=data, format="json")
        self.assertContains(
            response,
            "The fields project_id, org_unit_type_id must make a unique set.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    def test_create_missing_project_id(self):
        self.client.force_authenticate(self.user_misty)
        data = {
            "org_unit_type_id": self.ou_type_water_pokemons.id,
            "org_units_editable": False,
        }
        response = self.client.post(self.OUCRC_API_URL, data=data, format="json")
        self.assertContains(response, "This field is required.", status_code=status.HTTP_400_BAD_REQUEST)

        result = response.json()
        self.assertIn("project_id", result)
        self.assertIn("required", result["project_id"][0])

    def test_create_missing_org_unit_type_id(self):
        self.client.force_authenticate(self.user_brock)
        data = {
            "project_id": self.project_johto.id,
            "org_units_editable": False,
        }
        response = self.client.post(self.OUCRC_API_URL, data=data, format="json")
        self.assertContains(response, "This field is required.", status_code=status.HTTP_400_BAD_REQUEST)

        result = response.json()
        self.assertIn("org_unit_type_id", result)
        self.assertIn("required", result["org_unit_type_id"][0])

    def test_create_invalid_org_unit_type_id(self):
        self.client.force_authenticate(self.user_ash_ketchum)
        probably_not_a_valid_id = 1234567890
        data = {
            "project_id": self.project_johto.id,
            "org_unit_type_id": probably_not_a_valid_id,
            "org_units_editable": False,
        }
        response = self.client.post(self.OUCRC_API_URL, data=data, format="json")
        self.assertContains(response, f"Invalid pk", status_code=status.HTTP_400_BAD_REQUEST)

        result = response.json()
        self.assertIn("org_unit_type_id", result)
        self.assertIn(str(probably_not_a_valid_id), result["org_unit_type_id"][0])

    def test_create_invalid_editable_fields(self):
        self.client.force_authenticate(self.user_misty)
        pikachu = "PIKACHU"
        new_ou_type = self.create_new_org_unit_type("new ou type")
        data = {
            "project_id": self.project_johto.id,
            "org_unit_type_id": new_ou_type.id,
            "org_units_editable": False,
            "editable_fields": ["aliases", "name", pikachu],
        }
        response = self.client.post(self.OUCRC_API_URL, data=data, format="json")
        self.assertContains(
            response, f"The field '{pikachu}' is not a valid editable field.", status_code=status.HTTP_400_BAD_REQUEST
        )

    def test_create_invalid_possible_type_ids(self):
        new_org_unit_type = self.create_new_org_unit_type("new org unit type")
        data = {
            "org_unit_type_id": new_org_unit_type.id,
        }
        self.make_post_api_call_with_non_existing_id_in_attribute(
            attribute_name="possible_type_ids", additional_data=data
        )

    def test_create_invalid_possible_parent_type_ids(self):
        new_org_unit_type = self.create_new_org_unit_type("new org unit type")
        data = {
            "org_unit_type_id": new_org_unit_type.id,
        }
        self.make_post_api_call_with_non_existing_id_in_attribute(
            attribute_name="possible_parent_type_ids", additional_data=data
        )

    def test_create_invalid_group_set_ids(self):
        new_org_unit_type = self.create_new_org_unit_type("new org unit type")
        data = {
            "org_unit_type_id": new_org_unit_type.id,
        }
        self.make_post_api_call_with_non_existing_id_in_attribute(attribute_name="group_set_ids", additional_data=data)

    def test_create_invalid_editable_reference_form_ids(self):
        new_org_unit_type = self.create_new_org_unit_type("new org unit type")
        data = {
            "org_unit_type_id": new_org_unit_type.id,
        }
        self.make_post_api_call_with_non_existing_id_in_attribute(
            attribute_name="editable_reference_form_ids", additional_data=data
        )

    def test_create_invalid_other_group_ids(self):
        new_org_unit_type = self.create_new_org_unit_type("new org unit type")
        data = {
            "org_unit_type_id": new_org_unit_type.id,
        }
        self.make_post_api_call_with_non_existing_id_in_attribute(
            attribute_name="other_group_ids", additional_data=data
        )

    # *** Testing update PATCH endpoint ***
    def test_update_full(self):
        # Changing all the possible fields of this OUCRC
        self.client.force_authenticate(self.user_misty)
        data = {
            "org_units_editable": True,
            "editable_fields": m.OrgUnitChangeRequestConfiguration.LIST_OF_POSSIBLE_EDITABLE_FIELDS,
            "possible_type_ids": [
                self.ou_type_water_pokemons.id,
                self.ou_type_fire_pokemons.id,
                self.ou_type_rock_pokemons.id,
            ],
            "possible_parent_type_ids": [self.ou_type_water_pokemons.id, self.ou_type_rock_pokemons.id],
            "group_set_ids": [self.group_set_misty_pokemons.id],
            "editable_reference_form_ids": [self.form_water_gun.id, self.form_rock_throw.id],
            "other_group_ids": [self.other_group_1.id, self.other_group_2.id, self.other_group_3.id],
        }
        response = self.client.patch(f"{self.OUCRC_API_URL}{self.oucrc_type_water.id}/", data=data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.oucrc_type_water.refresh_from_db()
        oucrc = self.oucrc_type_water
        self.assertTrue(oucrc.org_units_editable)
        self.assertCountEqual(oucrc.editable_fields, data["editable_fields"])
        self.assertCountEqual(oucrc.possible_types.values_list("id", flat=True), data["possible_type_ids"])
        self.assertCountEqual(
            oucrc.possible_parent_types.values_list("id", flat=True), data["possible_parent_type_ids"]
        )
        self.assertCountEqual(oucrc.group_sets.values_list("id", flat=True), data["group_set_ids"])
        self.assertCountEqual(
            oucrc.editable_reference_forms.values_list("id", flat=True), data["editable_reference_form_ids"]
        )
        self.assertCountEqual(oucrc.other_groups.values_list("id", flat=True), data["other_group_ids"])
        self.assertEqual(oucrc.updated_by, self.user_misty)
        self.assertNotEqual(oucrc.created_by, oucrc.updated_at)

    def test_update_partial(self):
        # Changing only some fields of this OUCRC
        self.client.force_authenticate(self.user_brock)
        data = {
            "editable_fields": ["name"],
            "other_group_ids": [self.other_group_1.id, self.other_group_2.id, self.other_group_3.id],
        }
        response = self.client.patch(f"{self.OUCRC_API_URL}{self.oucrc_type_rock.id}/", data=data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.oucrc_type_rock.refresh_from_db()
        oucrc = self.oucrc_type_rock
        self.assertCountEqual(oucrc.editable_fields, data["editable_fields"])
        self.assertCountEqual(oucrc.other_groups.values_list("id", flat=True), data["other_group_ids"])
        self.assertEqual(oucrc.updated_by, self.user_brock)
        self.assertNotEqual(oucrc.created_by, oucrc.updated_at)

    def test_update_without_auth(self):
        data = {
            "org_units_editable": False,
        }
        response = self.client.patch(f"{self.OUCRC_API_URL}{self.oucrc_type_fire.id}/", data=data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_invalid_id(self):
        self.client.force_authenticate(self.user_ash_ketchum)
        data = {
            "org_units_editable": True,
        }
        probably_not_a_valid_id = 1234567890
        response = self.client.patch(f"{self.OUCRC_API_URL}{probably_not_a_valid_id}/", data=data, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_invalid_editable_fields(self):
        self.client.force_authenticate(self.user_ash_ketchum)
        pikachu = "PIKACHU"
        data = {
            "editable_fields": ["name", "aliases", pikachu, "closed_date"],
        }
        response = self.client.patch(f"{self.OUCRC_API_URL}{self.oucrc_type_fire.id}/", data=data, format="json")
        self.assertContains(response, pikachu, status_code=status.HTTP_400_BAD_REQUEST)

        result = response.json()
        self.assertIn("editable_fields", result)
        self.assertIn(pikachu, result["editable_fields"][0])

    def test_update_unknown_possible_types(self):
        self.make_patch_api_call_with_non_existing_id_in_attribute(attribute_name="possible_type_ids")

    def test_update_unknown_possible_parent_types(self):
        self.make_patch_api_call_with_non_existing_id_in_attribute(attribute_name="possible_parent_type_ids")

    def test_update_unknown_group_sets(self):
        self.make_patch_api_call_with_non_existing_id_in_attribute(attribute_name="group_set_ids")

    def test_update_unknown_editable_reference_forms(self):
        self.make_patch_api_call_with_non_existing_id_in_attribute(attribute_name="editable_reference_form_ids")

    def test_update_unknown_other_groups(self):
        self.make_patch_api_call_with_non_existing_id_in_attribute(attribute_name="other_group_ids")

    # + Test for updating groupsets or groups, but there were updates in groupsets between OUCRC creation and update
    # -> what should happen? error? cleanup without telling the user?

    # *** Testing DELETE endpoint ***
    def test_delete_ok(self):
        oucrcs_before_deletion = m.OrgUnitChangeRequestConfiguration.objects.count()
        self.client.force_authenticate(self.user_ash_ketchum)
        response = self.client.delete(f"{self.OUCRC_API_URL}{self.oucrc_type_fire.id}/", format="json")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        oucrcs_after_deletion = m.OrgUnitChangeRequestConfiguration.objects.count()
        self.assertEqual(oucrcs_before_deletion, oucrcs_after_deletion + 1)

        soft_deleted_oucrc = m.OrgUnitChangeRequestConfiguration.objects_only_deleted.get(id=self.oucrc_type_fire.id)
        self.assertIsNotNone(soft_deleted_oucrc.deleted_at)

    def test_delete_without_auth(self):
        response = self.client.delete(f"{self.OUCRC_API_URL}{self.oucrc_type_fire.id}/", format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_invalid_id(self):
        self.client.force_authenticate(self.user_ash_ketchum)
        probably_not_a_valid_id = 1234567890
        response = self.client.delete(f"{self.OUCRC_API_URL}{probably_not_a_valid_id}/", format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_error_deleting_and_recreating(self):
        # I'm not sure that we want this behavior, but that's what is implemented at the moment.

        # First, let's delete the existing OUCRC
        self.client.force_authenticate(self.user_ash_ketchum)
        response = self.client.delete(f"{self.OUCRC_API_URL}{self.oucrc_type_fire.id}/", format="json")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Then let's create a new OUCRC with the same project_id and org_unit_type_id as the one that was deleted
        # We don't care about the other parameters
        data = {
            "project_id": self.project_johto.id,
            "org_unit_type_id": self.ou_type_fire_pokemons.id,
            "org_units_editable": False,
        }
        response = self.client.post(self.OUCRC_API_URL, data=data, format="json")
        self.assertContains(
            response,
            f"There is already a configuration for this project_id ({self.project_johto.id}) and org_unit_type_id ({self.ou_type_fire_pokemons.id}).",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # + test for making sure that the user who deleted the OUCRC is stored in updated_by?
    # or have a field deleted_by?

    def test_check_availability_ok(self):
        # Preparing a new OrgUnitType in this project - since the 3 OUT already have an OUCRC in setUpTestData
        new_org_unit_type = self.create_new_org_unit_type("Psychic Pokémons")
        new_org_unit_type.projects.add(self.project_johto)
        new_org_unit_type.refresh_from_db()

        self.client.force_authenticate(self.user_ash_ketchum)
        response = self.client.get(
            f"{self.OUCRC_API_URL}check_availability/?project_id={self.project_johto.id}", format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected = {
            "id": new_org_unit_type.id,
            "name": new_org_unit_type.name,
        }
        self.assertEqual(response.json(), [expected])

    def test_check_availability_no_result(self):
        # All the OUCRCs have already been made for this project
        self.client.force_authenticate(self.user_ash_ketchum)
        response = self.client.get(
            f"{self.OUCRC_API_URL}check_availability/?project_id={self.project_johto.id}", format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [])

    def test_check_availability_no_config_yet(self):
        # Preparing a new Project and new OrgUnitTypes
        new_account = m.Account.objects.create(name="New account")
        new_project = m.Project.objects.create(name="New project", account=new_account, app_id="new")
        new_user = self.create_user_with_profile(username="New user", account=new_account)

        new_ou_type_1 = self.create_new_org_unit_type("new type 1")
        new_ou_type_1.projects.add(new_project)
        new_ou_type_1.refresh_from_db()
        new_ou_type_2 = self.create_new_org_unit_type("new type 2")
        new_ou_type_2.projects.add(new_project)
        new_ou_type_2.refresh_from_db()

        self.client.force_authenticate(new_user)
        response = self.client.get(
            f"{self.OUCRC_API_URL}check_availability/?project_id={new_project.id}", format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected = [
            {
                "id": new_ou_type_1.id,
                "name": new_ou_type_1.name,
            },
            {
                "id": new_ou_type_2.id,
                "name": new_ou_type_2.name,
            },
        ]
        self.assertEqual(response.json(), expected)

    def test_check_availability_without_auth(self):
        response = self.client.get(
            f"{self.OUCRC_API_URL}check_availability/?project_id={self.project_johto.id}", format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_check_availability_error_missing_parameter(self):
        self.client.force_authenticate(self.user_ash_ketchum)
        response = self.client.get(f"{self.OUCRC_API_URL}check_availability/", format="json")
        self.assertContains(
            response,
            "Parameter project_id is missing",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    def test_check_availability_invalid_project_id(self):
        probably_not_a_valid_id = 1234567890
        self.client.force_authenticate(self.user_ash_ketchum)
        response = self.client.get(
            f"{self.OUCRC_API_URL}check_availability/?project_id={probably_not_a_valid_id}", format="json"
        )
        self.assertContains(
            response,
            "This project does not exist",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # Add a test for checking availability for a project not assigned to the user, once implemented

    # def test_update_should_be_forbidden(self):
    #     self.client.force_authenticate(self.user_with_review_perm)
    #     change_request = m.OrgUnitChangeRequest.objects.create(org_unit=self.org_unit, new_name="Foo")
    #     data = {"new_name": "Baz"}
    #     response = self.client.put(f"/api/orgunits/changes/{change_request.pk}/", data=data, format="json")
    #     self.assertEqual(response.status_code, 405)
    #
    # def test_delete_should_be_forbidden(self):
    #     self.client.force_authenticate(self.user_with_review_perm)
    #     change_request = m.OrgUnitChangeRequest.objects.create(org_unit=self.org_unit, new_name="Foo")
    #     response = self.client.delete(f"/api/orgunits/changes/{change_request.pk}/", format="json")
    #     self.assertEqual(response.status_code, 405)
