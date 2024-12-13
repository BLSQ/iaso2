from rest_framework import status

from iaso.test import APITestCase
from iaso import models as m
from django.contrib.auth.models import Permission, Group


class UserRoleAPITestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org_unit_type = m.OrgUnitType.objects.create(name="Org unit type", short_name="OUT")

        cls.account = account = m.Account.objects.create(name="Account")
        cls.project = project = m.Project.objects.create(name="Project", account=account, app_id="foo.bar.baz")
        project.unit_types.set([cls.org_unit_type])

        cls.sw_source = sw_source = m.DataSource.objects.create(name="Galactic Empire")
        sw_source.projects.set([project])

        sw_version = m.SourceVersion.objects.create(data_source=sw_source, number=1)
        account.default_version = sw_version
        account.save()

        cls.user = cls.create_user_with_profile(username="yoda", account=account, permissions=["iaso_user_roles"])
        cls.user_with_no_permissions = cls.create_user_with_profile(username="userNoPermission", account=account)

        cls.permission = Permission.objects.create(
            name="iaso permission", content_type_id=1, codename="iaso_permission"
        )

        cls.permission1 = Permission.objects.create(
            name="iaso permission", content_type_id=1, codename="iaso_permission1"
        )

        cls.permission2 = Permission.objects.create(
            name="iaso permission", content_type_id=1, codename="iaso_permission2"
        )

        cls.permission_not_allowable = Permission.objects.create(
            name="admin permission", content_type_id=1, codename="admin_permission1"
        )
        cls.group = Group.objects.create(name=str(account.id) + "user role")

        cls.group.permissions.add(cls.permission)
        cls.group.refresh_from_db()
        cls.user_role = m.UserRole.objects.create(group=cls.group, account=account)
        cls.user_role.editable_org_unit_types.set([cls.org_unit_type])

    def test_create_user_role(self):
        self.client.force_authenticate(self.user)

        payload = {"name": "New user role name", "editable_org_unit_type_ids": [self.org_unit_type.id]}
        response = self.client.post("/api/userroles/", data=payload, format="json")

        r = self.assertJSONResponse(response, 201)

        self.assertEqual(r["name"], payload["name"])
        self.assertIsNotNone(r["id"])
        self.assertEqual(r["editable_org_unit_type_ids"], [self.org_unit_type.id])

    def test_create_user_role_without_name(self):
        self.client.force_authenticate(self.user)

        payload = {"permissions": ["iaso_mappings"]}
        response = self.client.post("/api/userroles/", data=payload, format="json")

        self.assertEqual(response.status_code, 400)

    def test_retrieve_user_role(self):
        self.client.force_authenticate(self.user)

        response = self.client.get(f"/api/userroles/{self.user_role.pk}/")

        r = self.assertJSONResponse(response, 200)
        self.assertEqual(r["id"], self.user_role.pk)
        self.user_role.refresh_from_db()
        expected_name = self.user_role.group.name.removeprefix(f"{self.account.id}_")
        self.assertEqual(r["name"], expected_name)
        self.assertEqual(r["editable_org_unit_type_ids"], [self.org_unit_type.id])

    def test_retrieve_user_role_read_only(self):
        self.client.force_authenticate(self.user_with_no_permissions)

        response = self.client.get(f"/api/userroles/{self.user_role.pk}/")

        r = self.assertJSONResponse(response, 200)
        self.assertEqual(r["id"], self.user_role.pk)
        self.assertEqual(r["editable_org_unit_type_ids"], [self.org_unit_type.id])

    def test_list_without_search(self):
        self.client.force_authenticate(self.user)

        response = self.client.get("/api/userroles/")

        r = self.assertJSONResponse(response, 200)
        self.assertEqual(len(r["results"]), 1)

    def test_list_with_search_on_user_role_name(self):
        self.client.force_authenticate(self.user)

        payload = {"search": "user role"}
        response = self.client.get("/api/userroles/", data=payload, format="json")

        r = self.assertJSONResponse(response, 200)

        self.assertEqual(len(r["results"]), 1)

        expected_name = self.user_role.group.name.removeprefix(f"{self.account.id}_")
        self.assertEqual(r["results"][0]["name"], expected_name)
        self.assertEqual(
            r["results"][0]["editable_org_unit_type_ids"],
            [self.org_unit_type.id],
        )

    def test_partial_update_invalid_org_unit_type(self):
        invalid_org_unit_type = m.OrgUnitType.objects.create(
            name="This org unit type is not linked to the account", short_name="Invalid"
        )

        self.client.force_authenticate(self.user)
        payload = {
            "name": self.user_role.group.name,
            "editable_org_unit_type_ids": [invalid_org_unit_type.pk],
        }

        response = self.client.put(f"/api/userroles/{self.user_role.id}/", data=payload, format="json")

        r = self.assertJSONResponse(response, 400)
        self.assertEqual(
            r["editable_org_unit_type_ids"],
            [
                f"`{invalid_org_unit_type.name} ({invalid_org_unit_type.pk})` is not a valid Org Unit Type for this account."
            ],
        )

    def test_partial_update_no_modification(self):
        new_org_unit_type = m.OrgUnitType.objects.create(name="New org unit type", short_name="NOUT")
        self.project.unit_types.add(new_org_unit_type.pk)

        self.client.force_authenticate(self.user)
        payload = {
            "name": self.user_role.group.name,
            "editable_org_unit_type_ids": [self.org_unit_type.id, new_org_unit_type.id],
        }

        response = self.client.put(f"/api/userroles/{self.user_role.id}/", data=payload, format="json")

        r = self.assertJSONResponse(response, 200)
        self.assertEqual(r["name"], payload["name"])
        self.assertEqual(r["editable_org_unit_type_ids"], [self.org_unit_type.id, new_org_unit_type.id])

    def test_partial_update_no_permission(self):
        self.client.force_authenticate(self.user_with_no_permissions)

        payload = {"name": self.user_role.group.name}
        response = self.client.put(f"/api/userroles/{self.user_role.id}/", data=payload, format="json")

        r = self.assertJSONResponse(response, 403)
        self.assertEqual(r["detail"], "You do not have permission to perform this action.")

    def test_update_name_modification(self):
        self.client.force_authenticate(self.user)

        payload = {"name": "user role modified"}
        response = self.client.put(f"/api/userroles/{self.user_role.id}/", data=payload, format="json")
        self.group.refresh_from_db()
        r = self.assertJSONResponse(response, 200)
        expected_name = self.user_role.group.name.removeprefix(f"{self.account.id}_")
        self.assertEqual(r["name"], expected_name)

    def test_partial_update_permissions_modification(self):
        self.client.force_authenticate(self.user)

        payload = {
            "name": self.user_role.group.name,
            "permissions": [self.permission1.codename, self.permission2.codename],
        }
        response = self.client.put(f"/api/userroles/{self.user_role.id}/", data=payload, format="json")

        r = self.assertJSONResponse(response, 200)
        self.assertEqual(
            [r["permissions"][0], r["permissions"][1]],
            [self.permission1.codename, self.permission2.codename],
        )

    def test_partial_update_not_allowable_permissions_modification(self):
        self.client.force_authenticate(self.user)

        payload = {
            "name": self.user_role.group.name,
            "permissions": [self.permission_not_allowable.codename],
        }
        response = self.client.put(f"/api/userroles/{self.user_role.id}/", data=payload, format="json")
        self.assertContains(response, "No Permission matches the given query", status_code=status.HTTP_404_NOT_FOUND)

    def test_delete_user_role(self):
        self.client.force_authenticate(self.user)

        response = self.client.delete(f"/api/userroles/{self.user_role.id}/")
        r = self.assertJSONResponse(response, 204)

    def test_delete_user_role_and_remove_users_in_it(self):
        self.client.force_authenticate(self.user)
        group_1 = Group.objects.create(name="Group 1")
        group_2 = Group.objects.create(name="Group 2")

        group_1.permissions.add(self.permission)
        group_2.permissions.add(self.permission)

        userRole_1 = m.UserRole.objects.create(group=group_1, account=self.account)
        userRole_2 = m.UserRole.objects.create(group=group_2, account=self.account)

        self.user.iaso_profile.user_roles.add(userRole_1)
        self.user.iaso_profile.user_roles.add(userRole_2)
        self.assertEqual(
            list(self.user.iaso_profile.user_roles.all()),
            list(m.UserRole.objects.filter(id__in=[userRole_2.id, userRole_1.id])),
        )
        response = self.client.delete(f"/api/userroles/{userRole_1.id}/")
        r = self.assertJSONResponse(response, 204)

        self.assertEqual(
            list(self.user.iaso_profile.user_roles.all()),
            list(m.UserRole.objects.filter(id__in=[userRole_2.id])),
        )

        self.assertFalse(Group.objects.filter(id=group_1.id).exists())
