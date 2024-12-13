import typing

import jsonschema
import numpy as np
import pandas as pd

from django.contrib.auth.models import Group, Permission
from django.core import mail
from django.test import override_settings
from django.utils.translation import gettext as _
from rest_framework import status

from hat.menupermissions import models as permission
from hat.menupermissions.constants import MODULES
from iaso import models as m
from iaso.models import Profile
from iaso.models.microplanning import Team
from iaso.test import APITestCase

name_and_id_schema = {
    "type": "object",
    "properties": {"id": {"type": "number"}, "name": {"type": "string"}},
    "required": ["name", "id"],
}

PROFILE_LOG_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "number"},
        "content-type": {"type": "string"},
        "object_id": {"type": "string"},
        "source": {"type": "string"},
        "created_at": {"type": "string"},
        "user": {
            "type": "object",
            "properties": {
                "id": {"type": "number"},
                "first_name": {"type": ["string", "null"]},
                "last_name": {"type": ["string", "null"]},
                "user_name": {"type": "string"},
                "email": {"type": ["string", "null"]},
                "language": {"type": ["string", "null"]},
                "phone_number": {"type": ["string", "null"]},
                "country_code": {"type": ["string", "null"]},
            },
            "required": ["id", "user_name"],
        },
        "past_value": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "pk": {"type": "number"},
                    "fields": {
                        "type": "object",
                        "properties": {
                            "user": {"type": "number"},
                            "first_name": {"type": ["string", "null"]},
                            "last_name": {"type": ["string", "null"]},
                            "username": {"type": ["string", "null"]},
                            "email": {"type": ["string", "null"]},
                            "organization": {"type": ["string", "null"]},
                            "user_permissions": {"type": "array", "items": {"type": "string"}},
                            "deleted_at": {"type": ["string", "null"]},
                            "account": {"type": "number"},
                            "dhis2_id": {"type": ["string", "null"]},
                            "language": {"type": ["string", "null"]},
                            "home_page": {"type": ["string", "null"]},
                            "projects": {"type": "array", "items": {"type": "number"}},
                            "org_units": {"type": "array", "items": {"type": "number"}},
                            "user_roles": {"type": "array", "items": {"type": "number"}},
                            "phone_number": {"type": ["string", "null"]},
                            "deleted_at": {"type": ["string", "null"]},
                        },
                        "required": ["user", "account"],
                    },
                },
            },
        },
        "new_value": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "pk": {"type": "number"},
                    "fields": {
                        "type": "object",
                        "properties": {
                            "user": {"type": "number"},
                            "first_name": {"type": ["string", "null"]},
                            "last_name": {"type": ["string", "null"]},
                            "username": {"type": ["string", "null"]},
                            "email": {"type": ["string", "null"]},
                            "organization": {"type": ["string", "null"]},
                            "user_permissions": {"type": "array", "items": {"type": "string"}},
                            "password_updated": {"type": "boolean"},
                            "deleted_at": {"type": ["string", "null"]},
                            "account": {"type": "number"},
                            "dhis2_id": {"type": ["string", "null"]},
                            "language": {"type": ["string", "null"]},
                            "home_page": {"type": ["string", "null"]},
                            "projects": {"type": "array", "items": {"type": "number"}},
                            "org_units": {"type": "array", "items": {"type": "number"}},
                            "user_roles": {"type": "array", "items": {"type": "number"}},
                            "phone_number": {"type": ["string", "null"]},
                            "deleted_at": {"type": ["string", "null"]},
                        },
                        "required": ["user"],
                    },
                },
            },
        },
    },
    "required": ["id", "user", "content_type", "source", "object_id", "created_at", "past_value", "new_value"],
}


class ProfileAPITestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.MODULES = [module["codename"] for module in MODULES]
        cls.account = m.Account.objects.create(name="Global Health Initiative", modules=cls.MODULES)
        cls.another_account = m.Account.objects.create(name="Another account")

        # TODO : make the org unit creations shorter and reusable
        cls.project = m.Project.objects.create(
            name="Hydroponic gardens",
            app_id="stars.empire.agriculture.hydroponics",
            account=cls.account,
        )
        datasource = m.DataSource.objects.create(name="Evil Empire")
        datasource.projects.add(cls.project)
        cls.datasource = datasource
        cls.sub_unit_type = m.OrgUnitType.objects.create(name="Jedi Squad", short_name="Jds")
        cls.parent_org_unit_type = m.OrgUnitType.objects.create(name="Jedi Council", short_name="Cnc")
        cls.parent_org_unit_type.sub_unit_types.add(cls.sub_unit_type)

        cls.mock_multipolygon = None
        cls.mock_point = None

        cls.org_unit_group = m.Group.objects.create(name="Elite councils")
        cls.datasource = datasource
        source_version_1 = m.SourceVersion.objects.create(data_source=datasource, number=1)
        cls.account.default_version = source_version_1
        cls.account.save()
        cls.org_unit_from_sub_type = m.OrgUnit.objects.create(
            org_unit_type=cls.sub_unit_type,
            version=source_version_1,
            name="Jedi Squad 1",
            geom=cls.mock_multipolygon,
            simplified_geom=cls.mock_multipolygon,
            catchment=cls.mock_multipolygon,
            location=cls.mock_point,
            validation_status=m.OrgUnit.VALIDATION_VALID,
            source_ref=None,
        )

        cls.org_unit_from_parent_type = m.OrgUnit.objects.create(
            org_unit_type=cls.parent_org_unit_type,
            version=source_version_1,
            name="Corruscant Jedi Council",
            geom=cls.mock_multipolygon,
            simplified_geom=cls.mock_multipolygon,
            catchment=cls.mock_multipolygon,
            location=cls.mock_point,
            validation_status=m.OrgUnit.VALIDATION_VALID,
            source_ref="FooBarB4z00",
        )
        cls.org_unit_from_parent_type.groups.set([cls.org_unit_group])

        cls.child_org_unit = m.OrgUnit.objects.create(
            org_unit_type=cls.parent_org_unit_type,
            version=source_version_1,
            name="Corruscant Jedi Council",
            geom=cls.mock_multipolygon,
            simplified_geom=cls.mock_multipolygon,
            catchment=cls.mock_multipolygon,
            location=cls.mock_point,
            validation_status=m.OrgUnit.VALIDATION_VALID,
            source_ref="PvtAI4RUMkr",
            parent=cls.org_unit_from_parent_type,
        )

        cls.permission = Permission.objects.create(
            name="iaso permission", content_type_id=1, codename="iaso_permission"
        )
        cls.group = Group.objects.create(name="user role")
        cls.group.permissions.add(cls.permission)
        cls.user_role = m.UserRole.objects.create(group=cls.group, account=cls.account)

        cls.group_another_account = Group.objects.create(name="user role with another account")
        cls.group_another_account.permissions.add(cls.permission)
        cls.user_role_another_account = m.UserRole.objects.create(
            group=cls.group_another_account, account=cls.another_account
        )

        # Users.
        cls.jane = cls.create_user_with_profile(
            username="janedoe", account=cls.account, permissions=[permission._FORMS]
        )
        cls.john = cls.create_user_with_profile(username="johndoe", account=cls.account, is_superuser=True)
        cls.jim = cls.create_user_with_profile(
            username="jim", account=cls.account, permissions=[permission._FORMS, permission._USERS_ADMIN]
        )
        cls.jam = cls.create_user_with_profile(
            username="jam",
            account=cls.account,
            permissions=[permission._USERS_MANAGED],
            language="en",
        )
        cls.jom = cls.create_user_with_profile(username="jom", account=cls.account, permissions=[], language="fr")
        cls.jum = cls.create_user_with_profile(
            username="jum", account=cls.account, permissions=[], projects=[cls.project]
        )
        cls.user_managed_geo_limit = cls.create_user_with_profile(
            username="managedGeoLimit",
            account=cls.account,
            permissions=[permission._USERS_MANAGED],
            org_units=[cls.org_unit_from_parent_type],
        )
        cls.team1 = Team.objects.create(project=cls.project, name="team1", manager=cls.jane)
        cls.team1.users.add(cls.jane)
        cls.team2 = Team.objects.create(project=cls.project, name="team2", manager=cls.jim)
        cls.team2.users.add(cls.jim)
        cls.user_managed_geo_limit.iaso_profile.user_roles.set([cls.user_role, cls.user_role_another_account])

        cls.user_role_name = cls.user_role.group.name.removeprefix(
            f"{cls.user_managed_geo_limit.iaso_profile.account.pk}_"
        )
        cls.user_role_another_account_name = cls.user_role_another_account.group.name.removeprefix(
            f"{cls.user_managed_geo_limit.iaso_profile.account.pk}_"
        )

    def test_can_delete_dhis2_id(self):
        self.client.force_authenticate(self.john)
        jim = Profile.objects.get(user=self.jim)
        jim.dhis2_id = "fsdgdfsgsdg"
        jim.save()

        data = {
            "id": str(self.jim.id),
            "user_name": "jim",
            "first_name": "",
            "last_name": "",
            "email": "",
            "password": "",
            "permissions": [],
            "org_units": [],
            "language": "fr",
            "dhis2_id": "",
        }

        response = self.client.patch("/api/profiles/{}/".format(jim.id), data=data, format="json")

        self.assertEqual(response.status_code, 200, response)

    def test_profile_me_without_auth(self):
        """GET /profiles/me/ without auth should result in a 401"""

        response = self.client.get("/api/profiles/me/")
        self.assertJSONResponse(response, 401)

    def test_profile_me_ok(self):
        """GET /profiles/me/ with auth"""

        self.client.force_authenticate(self.jane)
        response = self.client.get("/api/profiles/me/")
        self.assertJSONResponse(response, 200)

        response_data = response.json()
        self.assertValidProfileData(response_data)
        self.assertEqual(response_data["user_name"], "janedoe")
        self.assertHasField(response_data, "account", dict)
        self.assertHasField(response_data, "permissions", list)
        self.assertHasField(response_data, "is_superuser", bool)
        self.assertHasField(response_data, "org_units", list)

    def test_profile_me_superuser_ok(self):
        """GET /profiles/me/ with auth (superuser)"""

        self.client.force_authenticate(self.john)
        response = self.client.get("/api/profiles/me/")
        self.assertJSONResponse(response, 200)
        response_data = response.json()
        self.assertValidProfileData(response_data)
        self.assertEqual(response_data["user_name"], "johndoe")

    def test_profile_list_no_auth(self):
        """GET /profiles/ without auth -> 401"""

        response = self.client.get("/api/profiles/")
        self.assertJSONResponse(response, 401)

    def test_profile_list_read_only_permissions(self):
        """GET /profiles/ with auth (user has read only permissions)"""

        self.client.force_authenticate(self.jane)
        with self.assertNumQueries(12):
            response = self.client.get("/api/profiles/")
        self.assertJSONResponse(response, 200)
        profile_url = "/api/profiles/%s/" % self.jane.iaso_profile.id
        response = self.client.get(profile_url)
        self.assertJSONResponse(response, 200)
        response_data = response.json()
        self.assertValidProfileData(response_data)
        self.assertEqual(response_data["user_name"], "janedoe")
        response = self.client.patch(profile_url)
        self.assertJSONResponse(response, 403)

    def test_profile_list_ok(self):
        """GET /profiles/ with auth"""
        self.client.force_authenticate(self.jane)
        response = self.client.get("/api/profiles/")
        self.assertJSONResponse(response, 200)
        self.assertValidProfileListData(response.json(), 7)

    def test_profile_list_export_as_csv(self):
        self.john.iaso_profile.org_units.set([self.org_unit_from_sub_type, self.org_unit_from_parent_type])
        self.jum.iaso_profile.editable_org_unit_types.set([self.sub_unit_type])

        self.client.force_authenticate(self.jane)
        response = self.client.get("/api/profiles/?csv=true")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")

        response_csv = response.getvalue().decode("utf-8")

        expected_csv = (
            "username,"
            "password,"
            "email,"
            "first_name,"
            "last_name,"
            "orgunit,"
            "orgunit__source_ref,"
            "profile_language,"
            "dhis2_id,"
            "organization,"
            "permissions,"
            "user_roles,"
            "projects,"
            "phone_number,"
            "editable_org_unit_types\r\n"
        )

        expected_csv += "janedoe,,,,,,,,,,iaso_forms,,,,\r\n"
        expected_csv += f'johndoe,,,,,"{self.org_unit_from_sub_type.pk},{self.org_unit_from_parent_type.pk}",{self.org_unit_from_parent_type.source_ref},,,,,,,,\r\n'
        expected_csv += 'jim,,,,,,,,,,"iaso_forms,iaso_users",,,,\r\n'
        expected_csv += "jam,,,,,,,en,,,iaso_users_managed,,,,\r\n"
        expected_csv += "jom,,,,,,,fr,,,,,,,\r\n"
        expected_csv += f"jum,,,,,,,,,,,,{self.project.name},,{self.sub_unit_type.pk}\r\n"
        expected_csv += f'managedGeoLimit,,,,,{self.org_unit_from_parent_type.id},{self.org_unit_from_parent_type.source_ref},,,,iaso_users_managed,"{self.user_role_name},{self.user_role_another_account_name}",,,\r\n'

        self.assertEqual(response_csv, expected_csv)

    def test_profile_list_export_as_xlsx(self):
        self.john.iaso_profile.org_units.set([self.org_unit_from_sub_type, self.org_unit_from_parent_type])
        self.jum.iaso_profile.editable_org_unit_types.set([self.sub_unit_type])

        self.client.force_authenticate(self.jane)
        response = self.client.get("/api/profiles/?xlsx=true")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        excel_data = pd.read_excel(response.content, engine="openpyxl")

        excel_columns = list(excel_data.columns.ravel())
        self.assertEqual(
            excel_columns,
            [
                "username",
                "password",
                "email",
                "first_name",
                "last_name",
                "orgunit",
                "orgunit__source_ref",
                "profile_language",
                "dhis2_id",
                "organization",
                "permissions",
                "user_roles",
                "projects",
                "phone_number",
                "editable_org_unit_types",
            ],
        )

        data_dict = excel_data.replace({np.nan: None}).to_dict()

        self.assertDictEqual(
            data_dict,
            {
                "username": {0: "janedoe", 1: "johndoe", 2: "jim", 3: "jam", 4: "jom", 5: "jum", 6: "managedGeoLimit"},
                "password": {0: None, 1: None, 2: None, 3: None, 4: None, 5: None, 6: None},
                "email": {0: None, 1: None, 2: None, 3: None, 4: None, 5: None, 6: None},
                "first_name": {0: None, 1: None, 2: None, 3: None, 4: None, 5: None, 6: None},
                "last_name": {0: None, 1: None, 2: None, 3: None, 4: None, 5: None, 6: None},
                "orgunit": {
                    0: None,
                    1: f"{self.org_unit_from_sub_type.id},{self.org_unit_from_parent_type.id}",
                    2: None,
                    3: None,
                    4: None,
                    5: None,
                    6: f"{self.org_unit_from_parent_type.id}",
                },
                "orgunit__source_ref": {
                    0: None,
                    1: self.org_unit_from_parent_type.source_ref,
                    2: None,
                    3: None,
                    4: None,
                    5: None,
                    6: self.org_unit_from_parent_type.source_ref,
                },
                "profile_language": {0: None, 1: None, 2: None, 3: "en", 4: "fr", 5: None, 6: None},
                "dhis2_id": {0: None, 1: None, 2: None, 3: None, 4: None, 5: None, 6: None},
                "organization": {0: None, 1: None, 2: None, 3: None, 4: None, 5: None, 6: None},
                "permissions": {
                    0: "iaso_forms",
                    1: None,
                    2: "iaso_forms,iaso_users",
                    3: "iaso_users_managed",
                    4: None,
                    5: None,
                    6: "iaso_users_managed",
                },
                "user_roles": {
                    0: None,
                    1: None,
                    2: None,
                    3: None,
                    4: None,
                    5: None,
                    6: f"{self.user_role_name},{self.user_role_another_account_name}",
                },
                "projects": {0: None, 1: None, 2: None, 3: None, 4: None, 5: self.project.name, 6: None},
                "phone_number": {0: None, 1: None, 2: None, 3: None, 4: None, 5: None, 6: None},
                "editable_org_unit_types": {
                    0: None,
                    1: None,
                    2: None,
                    3: None,
                    4: None,
                    5: self.sub_unit_type.pk,
                    6: None,
                },
            },
        )

    def test_profile_list_user_admin_ok(self):
        """GET /profiles/ with auth (user has user admin permissions)"""
        self.client.force_authenticate(self.jim)
        response = self.client.get("/api/profiles/")
        self.assertJSONResponse(response, 200)
        self.assertValidProfileListData(response.json(), 7)

    def test_profile_list_superuser_ok(self):
        """GET /profiles/ with auth (superuser)"""
        self.client.force_authenticate(self.john)
        response = self.client.get("/api/profiles/")
        self.assertJSONResponse(response, 200)
        self.assertValidProfileListData(response.json(), 7)

    def test_profile_list_user_manager_ok(self):
        """GET /profiles/ with auth (superuser)"""
        self.client.force_authenticate(self.jam)
        response = self.client.get("/api/profiles/")
        self.assertJSONResponse(response, 200)
        self.assertValidProfileListData(response.json(), 7)

    def test_profile_list_managed_user_only_superuser(self):
        """GET /profiles/ with auth (superuser)"""
        self.client.force_authenticate(self.john)
        response = self.client.get("/api/profiles/?managedUsersOnly=true")
        self.assertJSONResponse(response, 200)
        self.assertValidProfileListData(response.json(), 7)

    def test_profile_list_managed_user_only_user_admin(self):
        """GET /profiles/ with auth (superuser)"""
        self.client.force_authenticate(self.john)
        response = self.client.get("/api/profiles/?managedUsersOnly=true")
        self.assertJSONResponse(response, 200)
        self.assertValidProfileListData(response.json(), 7)

    def test_profile_list_managed_user_only_user_manager_no_org_unit(self):
        """GET /profiles/ with auth (superuser)"""
        self.client.force_authenticate(self.jam)
        response = self.client.get("/api/profiles/?managedUsersOnly=true")
        self.assertJSONResponse(response, 200)
        self.assertValidProfileListData(response.json(), 6)

    def test_profile_list_managed_user_only_user_manager_with_org_unit(self):
        """GET /profiles/ with auth (superuser)"""
        self.jam.iaso_profile.org_units.set([self.org_unit_from_parent_type.id])
        self.jum.iaso_profile.org_units.set([self.child_org_unit.id])
        self.client.force_authenticate(self.jam)
        response = self.client.get("/api/profiles/?managedUsersOnly=true")
        self.assertJSONResponse(response, 200)
        self.assertValidProfileListData(response.json(), 2)

    def test_profile_list_managed_user_only_user_regular_user(self):
        """GET /profiles/ with auth (superuser)"""
        self.client.force_authenticate(self.jane)
        response = self.client.get("/api/profiles/?managedUsersOnly=true")
        self.assertJSONResponse(response, 200)
        self.assertValidProfileListData(response.json(), 0)

    def assertValidProfileListData(self, list_data: typing.Mapping, expected_length: int, paginated: bool = False):
        self.assertValidListData(
            list_data=list_data,
            expected_length=expected_length,
            results_key="profiles",
            paginated=paginated,
        )

        for profile_data in list_data["profiles"]:
            self.assertValidProfileData(profile_data)

    def test_create_profile_no_perm(self):
        self.client.force_authenticate(self.jane)
        data = {
            "user_name": "unittest_user_name",
            "password": "unittest_password",
            "first_name": "unittest_first_name",
            "last_name": "unittest_last_name",
        }
        response = self.client.post("/api/profiles/", data=data, format="json")

        self.assertEqual(response.status_code, 403)

    def test_create_user_with_user_roles_and_permissions(self):
        self.client.force_authenticate(self.jim)
        data = {
            "user_name": "unittest_user_name",
            "password": "unittest_password",
            "first_name": "unittest_first_name",
            "last_name": "unittest_last_name",
            "email": "unittest_last_name",
            "user_permissions": ["iaso_forms"],
            "user_roles": [self.user_role.id],
        }
        response = self.client.post("/api/profiles/", data=data, format="json")
        self.assertEqual(response.status_code, 200)

        response_data = response.json()
        user_user_role = m.UserRole.objects.get(pk=response_data["user_roles"][0])
        self.assertValidProfileData(response_data)
        self.assertEqual(user_user_role.id, self.user_role.id)
        self.assertEqual(user_user_role.group.name, self.group.name)

        user = m.User.objects.get(username="unittest_user_name")
        self.assertEqual(user.user_permissions.count(), 1)
        self.assertEqual(user.user_permissions.first().codename, "iaso_forms")

    def test_create_user_should_fail_with_restricted_editable_org_unit_types_for_field_orgunits(self):
        """
        The user is restricted to one org unit type.
        Creating a user with unauthorized values in `org_units` should fail.
        """
        user = self.jam

        self.assertTrue(user.has_perm(permission.USERS_MANAGED))
        self.assertFalse(user.has_perm(permission.USERS_ADMIN))
        self.assertEqual(self.org_unit_from_sub_type.org_unit_type_id, self.sub_unit_type.id)

        user.iaso_profile.org_units.set([self.org_unit_from_parent_type])
        user.iaso_profile.editable_org_unit_types.set(
            # Only org units of this type is now writable.
            [self.sub_unit_type]
        )

        self.client.force_authenticate(user)
        data = {
            "user_name": "unittest_user_name",
            "password": "unittest_password",
            "first_name": "unittest_first_name",
            "last_name": "unittest_last_name",
            "email": "unittest_last_name",
            "user_permissions": ["iaso_forms"],
            "user_roles": [self.user_role.id],
            "org_units": [{"id": self.org_unit_from_parent_type.id}],
        }

        response = self.client.post("/api/profiles/", data=data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"],
            f"The user does not have rights on the following org unit types: {self.parent_org_unit_type.name}",
        )

    def test_create_user_should_fail_with_restricted_editable_org_unit_types_for_field_editableorgunittypeids(self):
        """
        The user is restricted to one org unit type.
        Creating a user with unauthorized values in `editable_org_unit_type_ids` should fail.
        """
        user = self.jam

        self.assertTrue(user.has_perm(permission.USERS_MANAGED))
        self.assertFalse(user.has_perm(permission.USERS_ADMIN))

        user.iaso_profile.org_units.set([self.org_unit_from_parent_type])
        user.iaso_profile.editable_org_unit_types.set(
            # Only org units of this type is now writable.
            [self.sub_unit_type]
        )

        self.client.force_authenticate(user)

        data = {
            "user_name": "user_name",
            "password": "password",
            "first_name": "first_name",
            "last_name": "last_name",
            "email": "test@test.com",
            "org_units": [{"id": self.org_unit_from_parent_type.id}],
            "editable_org_unit_type_ids": [self.parent_org_unit_type.id],
        }

        response = self.client.post("/api/profiles/", data=data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"], "The user does not have rights on the following org unit types: Jedi Council"
        )

    def test_create_user_with_not_allowed_user_roles(self):
        self.client.force_authenticate(self.jim)
        data = {
            "user_name": "unittest_user_name",
            "password": "unittest_password",
            "first_name": "unittest_first_name",
            "last_name": "unittest_last_name",
            "email": "unittest_last_name",
            "user_permissions": ["iaso_forms"],
            "user_roles": [self.user_role.id, self.user_role_another_account.id],
        }
        response = self.client.post("/api/profiles/", data=data, format="json")
        self.assertContains(response, "No UserRole matches the given query", status_code=status.HTTP_404_NOT_FOUND)

    def test_create_profile_duplicate_user(self):
        self.client.force_authenticate(self.jim)
        data = {
            "user_name": "janedoe",
            "password": "unittest_password",
            "first_name": "unittest_first_name",
            "last_name": "unittest_last_name",
        }
        response = self.client.post("/api/profiles/", data=data, format="json")
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertEqual(response_data["errorKey"], "user_name")

    def test_create_profile_duplicate_user_with_capitale_letters(self):
        self.client.force_authenticate(self.jim)
        data = {
            "user_name": "JaNeDoE",
            "password": "unittest_password",
            "first_name": "unittest_first_name",
            "last_name": "unittest_last_name",
        }
        response = self.client.post("/api/profiles/", data=data, format="json")
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertEqual(response_data["errorKey"], "user_name")

    def test_create_profile_then_delete(self):
        self.client.force_authenticate(self.jim)
        data = {
            "user_name": "unittest_user_name",
            "password": "unittest_password",
            "first_name": "unittest_first_name",
            "last_name": "unittest_last_name",
            "email": "unittest_last_name",
        }
        response = self.client.post("/api/profiles/", data=data, format="json")
        self.assertEqual(response.status_code, 200)

        response_data = response.json()
        self.assertValidProfileData(response_data)
        self.assertEqual(response_data["user_name"], "unittest_user_name")
        self.assertEqual(response_data["is_superuser"], False)

        profile = m.Profile.objects.get(pk=response_data["id"])
        user = profile.user
        self.assertEqual(user.username, data["user_name"])
        self.assertEqual(user.first_name, data["first_name"])
        self.assertQuerySetEqual(user.user_permissions.all(), [])
        self.assertEqual(m.User.objects.filter(username=data["user_name"]).count(), 1)
        # check that we have copied the account from the creator account
        self.assertEqual(profile.account, self.account)

        profile_id = profile.id
        user_id = user.id
        response = self.client.delete(f"/api/profiles/{profile_id}/")

        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(m.User.objects.filter(id=user_id), [])
        self.assertQuerySetEqual(m.Profile.objects.filter(id=profile_id), [])

    def test_create_profile_with_org_units_and_perms(self):
        self.client.force_authenticate(self.jim)
        data = {
            "user_name": "unittest_user_name",
            "password": "unittest_password",
            "first_name": "unittest_first_name",
            "last_name": "unittest_last_name",
            "email": "unittest_last_name",
            "org_units": [{"id": self.org_unit_from_parent_type.id}],
            "user_permissions": ["iaso_forms"],
            "editable_org_unit_type_ids": [self.sub_unit_type.id],
        }
        response = self.client.post("/api/profiles/", data=data, format="json")
        self.assertEqual(response.status_code, 200)

        response_data = response.json()
        self.assertValidProfileData(response_data)
        self.assertEqual(response_data["user_name"], "unittest_user_name")
        self.assertEqual(response_data["is_superuser"], False)

        profile = m.Profile.objects.get(pk=response_data["id"])
        self.assertEqual(profile.editable_org_unit_types.count(), 1)
        self.assertEqual(profile.editable_org_unit_types.first(), self.sub_unit_type)

        user = profile.user
        self.assertEqual(user.username, data["user_name"])
        self.assertEqual(user.first_name, data["first_name"])

        self.assertEqual(m.User.objects.filter(username=data["user_name"]).count(), 1)
        self.assertEqual(profile.account, self.account)

        self.assertQuerySetEqual(
            user.user_permissions.all(),
            ["<Permission: Menupermissions | custom permission support | Formulaires>"],
            transform=repr,
        )
        org_units = profile.org_units.all()
        self.assertEqual(org_units.count(), 1)
        self.assertEqual(org_units[0].name, "Corruscant Jedi Council")

    @override_settings(DEFAULT_FROM_EMAIL="sender@test.com", DNS_DOMAIN="iaso-test.bluesquare.org")
    def test_create_profile_with_send_email(self):
        self.client.force_authenticate(self.jim)
        data = {
            "user_name": "userTest",
            "password": "",
            "first_name": "unittest_first_name",
            "last_name": "unittest_last_name",
            "send_email_invitation": True,
            "email": "test@test.com",
        }

        response = self.client.post("/api/profiles/", data=data, format="json")
        self.assertEqual(response.status_code, 200)

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.subject, "Set up a password for your new account on iaso-test.bluesquare.org")
        self.assertEqual(email.from_email, "sender@test.com")
        self.assertEqual(email.to, ["test@test.com"])
        self.assertIn(f"http://iaso-test.bluesquare.org", email.body)
        self.assertIn(f"The iaso-test.bluesquare.org Team.", email.body)

    def test_create_profile_with_no_password_and_not_send_email(self):
        self.client.force_authenticate(self.jim)
        data = {
            "user_name": "userTest",
            "password": "",
            "first_name": "unittest_first_name",
            "last_name": "unittest_last_name",
            "send_email_invitation": False,
            "email": "test@test.com",
        }

        response = self.client.post("/api/profiles/", data=data, format="json")
        self.assertEqual(response.status_code, 400)

        response_data = response.json()
        self.assertEqual(response_data["errorKey"], "password")

    def test_create_profile_with_managed_geo_limit(self):
        self.client.force_authenticate(self.user_managed_geo_limit)
        data = {
            "user_name": "unittest_user_name",
            "password": "unittest_password",
            "first_name": "unittest_first_name",
            "last_name": "unittest_last_name",
            "email": "unittest_last_name",
            "org_units": [{"id": self.child_org_unit.id}],
            "user_permissions": ["iaso_forms"],
        }

        response = self.client.post("/api/profiles/", data=data, format="json")
        self.assertEqual(response.status_code, 200)

        response_data = response.json()

        self.assertValidProfileData(response_data)
        self.assertEqual(response_data["user_name"], "unittest_user_name")
        self.assertEqual(response_data["is_superuser"], False)

        profile = m.Profile.objects.get(pk=response_data["id"])
        user = profile.user
        self.assertEqual(user.username, data["user_name"])
        self.assertEqual(user.first_name, data["first_name"])

        self.assertEqual(m.User.objects.filter(username=data["user_name"]).count(), 1)
        self.assertEqual(profile.account, self.account)

        self.assertQuerySetEqual(
            user.user_permissions.all(),
            ["<Permission: Menupermissions | custom permission support | Formulaires>"],
            transform=repr,
        )
        org_units = profile.org_units.all()
        self.assertEqual(org_units.count(), 1)
        self.assertEqual(org_units[0].name, "Corruscant Jedi Council")

    def test_create_profile_without_org_unit_with_managed_geo_limit(self):
        self.client.force_authenticate(self.user_managed_geo_limit)
        data = {
            "user_name": "unittest_user_name",
            "password": "unittest_password",
            "first_name": "unittest_first_name",
            "last_name": "unittest_last_name",
            "email": "unittest_last_name",
            "user_permissions": ["iaso_forms"],
        }
        response = self.client.post("/api/profiles/", data=data, format="json")

        self.assertEqual(response.status_code, 403)

    def assertValidProfileData(self, project_data: typing.Mapping):
        self.assertHasField(project_data, "id", int)
        self.assertHasField(project_data, "first_name", str)
        self.assertHasField(project_data, "last_name", str)
        self.assertHasField(project_data, "email", str)

    def test_delete_profile_no_perm(self):
        self.client.force_authenticate(self.jane)
        response = self.client.delete("/api/profiles/1/")

        self.assertEqual(response.status_code, 403)

    def test_profile_error_dhis2_constraint(self):
        # Test for regression of IA-1249
        self.client.force_authenticate(self.jim)
        data = {"user_name": "unittest_user1", "password": "unittest_password", "dhis2_id": ""}
        response = self.client.post("/api/profiles/", data=data, format="json")
        self.assertEqual(response.status_code, 200, response.content)

        data = {"user_name": "unittest_user2", "password": "unittest_password", "dhis2_id": ""}
        response = self.client.post("/api/profiles/", data=data, format="json")

        self.assertEqual(response.status_code, 200, response.content)
        profile1 = m.Profile.objects.get(user__username="unittest_user1")
        profile2 = m.Profile.objects.get(user__username="unittest_user2")
        self.assertNotEqual(profile1.account_id, None)
        self.assertEqual(profile2.account_id, profile1.account_id)
        self.assertEqual(profile2.dhis2_id, None)

        data = {"user_name": "unittest_user2", "password": "unittest_password", "dhis2_id": "", "first_name": "test"}
        response = self.client.patch(f"/api/profiles/{profile2.id}/", data=data, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        profile2.refresh_from_db()
        self.assertEqual(profile2.dhis2_id, None)

        data = {"user_name": "unittest_user2", "password": "unittest_password", "dhis2_id": "test_dhis2_id"}
        response = self.client.patch(f"/api/profiles/{profile2.id}/", data=data, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        profile2.refresh_from_db()
        self.assertEqual(profile2.dhis2_id, "test_dhis2_id")

    def test_account_feature_flags_is_included(self):
        aff = m.AccountFeatureFlag.objects.create(code="shape", name="Can edit shape")
        m.AccountFeatureFlag.objects.create(code="not-used", name="this is not used")
        self.client.force_authenticate(self.jane)

        # no feature flag at first
        response = self.client.get("/api/profiles/me/")
        self.assertJSONResponse(response, 200)
        response_data = response.json()
        self.assertIn("account", response_data)
        self.assertEqual(response_data["account"]["feature_flags"], [])

        # add a feature flags
        self.account.feature_flags.add(aff)

        response = self.client.get("/api/profiles/me/")
        self.assertJSONResponse(response, 200)
        response_data = response.json()
        self.assertIn("account", response_data)

        self.assertEqual(response_data["account"]["feature_flags"], ["shape"])

        # remove feature flags
        self.account.feature_flags.remove(aff)
        response = self.client.get("/api/profiles/me/")
        self.assertJSONResponse(response, 200)
        response_data = response.json()
        self.assertIn("account", response_data)

        self.assertEqual(response_data["account"]["feature_flags"], [])

    def test_search_user_by_permissions(self):
        self.client.force_authenticate(self.jane)

        response = self.client.get("/api/profiles/?permissions=iaso_users")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["profiles"][0]["user_name"], "jim")
        self.assertEqual(len(response.json()["profiles"]), 1)

    def test_search_user_by_org_units(self):
        self.client.force_authenticate(self.jane)
        self.jane.iaso_profile.org_units.set([self.org_unit_from_parent_type])

        response = self.client.get(f"/api/profiles/?location={self.org_unit_from_parent_type.pk}&limit=100")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["profiles"][0]["user_name"], "janedoe")
        self.assertEqual(len(response.json()["profiles"]), 2)

    def test_search_user_by_org_units_type(self):
        self.client.force_authenticate(self.jane)
        self.jane.iaso_profile.org_units.set([self.org_unit_from_parent_type])

        response = self.client.get(f"/api/profiles/?orgUnitTypes={self.parent_org_unit_type.pk}&limit=100")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["profiles"][0]["user_name"], "janedoe")
        self.assertEqual(len(response.json()["profiles"]), 2)

    def test_search_user_by_children_ou(self):
        self.client.force_authenticate(self.jane)
        self.jane.iaso_profile.org_units.set([self.child_org_unit])

        response = self.client.get(
            f"/api/profiles/?location={self.org_unit_from_parent_type.pk}&ouParent=false&ouChildren=true"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["profiles"][0]["user_name"], "janedoe")
        self.assertEqual(len(response.json()["profiles"]), 2)

    def test_search_user_by_parent_ou(self):
        self.client.force_authenticate(self.jane)
        self.jane.iaso_profile.org_units.set([self.org_unit_from_parent_type])

        response = self.client.get(
            f"/api/profiles/?location={self.child_org_unit.pk}&ouParent=true&ouChildren=false&limit=100"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["profiles"][0]["user_name"], "janedoe")
        self.assertEqual(len(response.json()["profiles"]), 2)

    def test_search_by_ids(self):
        self.client.force_authenticate(self.jane)
        response = self.client.get(f"/api/profiles/", {"ids": f"{self.jane.id},{self.jim.id}"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["profiles"]), 2)
        self.assertEqual(response.json()["profiles"][0]["user_name"], "janedoe")
        self.assertEqual(response.json()["profiles"][1]["user_name"], "jim")

    def test_search_by_teams(self):
        self.client.force_authenticate(self.jane)
        response = self.client.get(f"/api/profiles/", {"teams": f"{self.team1.pk},{self.team2.pk}"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["profiles"]), 2)
        user_names = [item["user_name"] for item in response.data["profiles"]]
        self.assertIn("janedoe", user_names)
        self.assertIn("jim", user_names)

    def test_user_with_managed_permission_can_update_profile_of_user_in_sub_org_unit(self):
        self.jam.iaso_profile.org_units.set([self.org_unit_from_parent_type.id])
        self.jum.iaso_profile.org_units.set([self.child_org_unit.id])
        self.client.force_authenticate(self.jam)
        jum = Profile.objects.get(user=self.jum)
        data = {
            "user_name": "unittest_user_name",
            "password": "unittest_password",
            "first_name": "unittest_first_name",
            "last_name": "unittest_last_name",
            "user_permissions": [permission._FORMS, permission._USERS_MANAGED],
        }
        response = self.client.patch(f"/api/profiles/{jum.id}/", data=data, format="json")
        self.assertEqual(response.status_code, 200)

    def test_user_with_managed_permission_without_location_can_update_profile_of_user_in_whole_pyramid(self):
        self.jum.iaso_profile.org_units.set([self.child_org_unit.id])
        self.client.force_authenticate(self.jam)
        jum = Profile.objects.get(user=self.jum)
        data = {
            "user_name": "unittest_user_name",
            "password": "unittest_password",
            "first_name": "unittest_first_name",
            "last_name": "unittest_last_name",
            "org_units": [{"id": self.org_unit_from_parent_type.id}],
            "user_permissions": [permission._FORMS, permission._USERS_MANAGED],
        }
        response = self.client.patch(f"/api/profiles/{jum.id}/", data=data, format="json")
        jum.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(jum.org_units.values_list("id", flat=True)), [self.org_unit_from_parent_type.id])

    def test_user_with_managed_permission_cannot_grant_user_admin_permission(self):
        self.jam.iaso_profile.org_units.set([self.org_unit_from_parent_type.id])
        self.jum.iaso_profile.org_units.set([self.child_org_unit.id])
        self.client.force_authenticate(self.jam)
        jum = Profile.objects.get(user=self.jum)
        data = {
            "user_name": "jum",
            "user_permissions": [permission._FORMS, permission._USERS_MANAGED, permission._USERS_ADMIN],
        }
        response = self.client.patch(f"/api/profiles/{jum.id}/", data=data, format="json")
        self.assertEqual(response.status_code, 403)

    def test_user_with_managed_permission_cannot_grant_user_admin_permission_through_user_roles(self):
        group = Group.objects.create(name="admin")
        group.permissions.set([Permission.objects.get(codename=permission._USERS_ADMIN)])
        role = m.UserRole.objects.create(account=self.account, group=group)
        self.jam.iaso_profile.org_units.set([self.org_unit_from_parent_type.id])
        self.jum.iaso_profile.org_units.set([self.child_org_unit.id])
        self.client.force_authenticate(self.jam)
        jum = Profile.objects.get(user=self.jum)
        data = {
            "user_name": "jum",
            "user_roles": [role.id],
        }
        response = self.client.patch(f"/api/profiles/{jum.id}/", data=data, format="json")
        self.assertEqual(response.status_code, 403)

    def test_user_with_managed_permission_can_grant_user_roles(self):
        group = Group.objects.create(name="admin")
        group.permissions.set([Permission.objects.get(codename=permission._FORMS)])
        role = m.UserRole.objects.create(account=self.account, group=group)
        self.jam.iaso_profile.org_units.set([self.org_unit_from_parent_type.id])
        self.jum.iaso_profile.org_units.set([self.child_org_unit.id])
        self.client.force_authenticate(self.jam)
        jum = Profile.objects.get(user=self.jum)
        data = {
            "user_name": "jum",
            "user_roles": [role.id],
        }
        response = self.client.patch(f"/api/profiles/{jum.id}/", data=data, format="json")
        self.assertEqual(response.status_code, 200)

    def test_user_with_managed_permission_can_assign_org_unit_within_their_health_pyramid(self):
        self.jam.iaso_profile.org_units.set([self.org_unit_from_parent_type.id])
        self.jum.iaso_profile.org_units.set([self.child_org_unit.id])
        self.client.force_authenticate(self.jam)
        jum = Profile.objects.get(user=self.jum)
        data = {
            "user_name": "jum",
            "org_units": [{"id": self.org_unit_from_parent_type.id}],
        }
        response = self.client.patch(f"/api/profiles/{jum.id}/", data=data, format="json")
        self.assertEqual(response.status_code, 200)

    def test_user_with_managed_permission_can_assign_org_unit_within_their_health_pyramid_with_existing_ones_outside(
        self,
    ):
        self.jam.iaso_profile.org_units.set([self.org_unit_from_parent_type.id])
        self.jum.iaso_profile.org_units.set([self.child_org_unit.id, self.org_unit_from_sub_type])
        self.client.force_authenticate(self.jam)
        jum = Profile.objects.get(user=self.jum)
        data = {
            "user_name": "jum",
            "org_units": [{"id": self.org_unit_from_parent_type.id}, {"id": self.org_unit_from_sub_type.id}],
        }
        response = self.client.patch(f"/api/profiles/{jum.id}/", data=data, format="json")
        self.assertEqual(response.status_code, 200)

    def test_user_with_managed_permission_cannot_assign_org_unit_outside_of_their_health_pyramid(self):
        self.jam.iaso_profile.org_units.set([self.org_unit_from_parent_type.id])
        self.jum.iaso_profile.org_units.set([self.child_org_unit.id])
        self.client.force_authenticate(self.jam)
        jum = Profile.objects.get(user=self.jum)
        data = {
            "user_name": "jum",
            "org_units": [{"id": self.org_unit_from_sub_type.id}],
        }
        response = self.client.patch(f"/api/profiles/{jum.id}/", data=data, format="json")
        self.assertEqual(response.status_code, 403)

    def test_user_with_managed_permission_cannot_update_profile_of_user_not_in_sub_org_unit(self):
        self.jam.iaso_profile.org_units.set([self.org_unit_from_parent_type.id])
        self.client.force_authenticate(self.jam)
        data = {
            "user_name": "unittest_user_name",
            "password": "unittest_password",
            "first_name": "unittest_first_name",
            "last_name": "unittest_last_name",
        }
        jum = Profile.objects.get(user=self.jum)
        response = self.client.patch(f"/api/profiles/{jum.id}/", data=data, format="json")
        self.assertEqual(response.status_code, 403)

    def test_user_with_managed_permission_can_update_profile_if_not_themselves_in_sub_org_unit(self):
        self.jum.iaso_profile.org_units.set([self.org_unit_from_parent_type.id])
        self.client.force_authenticate(self.jam)
        data = {
            "user_name": "unittest_user_name",
            "password": "unittest_password",
            "first_name": "unittest_first_name",
            "last_name": "unittest_last_name",
        }
        jum = Profile.objects.get(user=self.jum)
        response = self.client.patch(f"/api/profiles/{jum.id}/", data=data, format="json")
        self.assertEqual(response.status_code, 200)

    def test_update_user_should_fail_when_assigning_an_org_unit_outside_of_the_author_own_health_pyramid(self):
        user = self.jam
        user.iaso_profile.org_units.set([self.org_unit_from_sub_type])

        self.assertTrue(user.has_perm(permission.USERS_MANAGED))
        self.assertFalse(user.has_perm(permission.USERS_ADMIN))

        profile_to_modify = Profile.objects.get(user=self.jum)
        profile_to_modify.org_units.set([self.org_unit_from_sub_type])

        self.client.force_authenticate(user)
        data = {
            "user_name": "new_user_name",
            "org_units": [
                {"id": self.org_unit_from_parent_type.pk},
                {"id": "foo"},
                {"bar": "foo"},
            ],
        }
        response = self.client.patch(f"/api/profiles/{profile_to_modify.pk}/", data=data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"],
            (
                f"User with menupermissions.iaso_users_managed cannot assign an OrgUnit outside "
                f"of their own health pyramid. Trying to assign {self.org_unit_from_parent_type.pk}."
            ),
        )

    def test_update_user_should_fail_with_restricted_editable_org_unit_types_for_field_editableorgunittypeids(self):
        """
        The user is restricted to one org unit type.
        Updating a user with unauthorized values in `editable_org_unit_type_ids` should fail.
        """
        user = self.jam

        self.assertTrue(user.has_perm(permission.USERS_MANAGED))
        self.assertFalse(user.has_perm(permission.USERS_ADMIN))

        user.iaso_profile.editable_org_unit_types.set(
            # Only org units of this type is now writable.
            [self.sub_unit_type]
        )

        self.client.force_authenticate(user)
        jum = Profile.objects.get(user=self.jum)

        data = {
            "user_name": "new_user_name",
            "editable_org_unit_type_ids": [self.sub_unit_type.id],
        }
        response = self.client.patch(f"/api/profiles/{jum.id}/", data=data, format="json")
        self.assertEqual(response.status_code, 200)

        data = {
            "user_name": "new_user_name",
            "editable_org_unit_type_ids": [self.parent_org_unit_type.id],
        }
        response = self.client.patch(f"/api/profiles/{jum.id}/", data=data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"], "The user does not have rights on the following org unit types: Jedi Council"
        )

    def test_update_user_should_succeed_with_restricted_editable_org_unit_types_when_modifying_another_field(self):
        """
        A user restricted to a given OrgUnitType should be able to edit another user as long as
        he's not modifying the `org_units` or `editable_org_unit_type_ids` fields.
        """
        user = self.jam

        self.assertTrue(user.has_perm(permission.USERS_MANAGED))
        self.assertFalse(user.has_perm(permission.USERS_ADMIN))

        user.iaso_profile.org_units.set([self.org_unit_from_parent_type])
        user.iaso_profile.editable_org_unit_types.set(
            # Only org units of this type is now writable.
            [self.sub_unit_type]
        )

        jum_profile = Profile.objects.get(user=self.jum)
        jum_profile.org_units.set([self.org_unit_from_parent_type])
        jum_profile.editable_org_unit_types.set(
            # Only org units of this type is now writable.
            [self.parent_org_unit_type]
        )

        self.client.force_authenticate(user)

        data = {
            "user_name": "new_user_name",
            "org_units": [{"id": self.org_unit_from_parent_type.id}],
            "editable_org_unit_type_ids": [self.parent_org_unit_type.id],
        }
        response = self.client.patch(f"/api/profiles/{jum_profile.id}/", data=data, format="json")
        self.assertEqual(response.status_code, 200)
        self.jum.refresh_from_db()
        self.assertEqual(self.jum.username, "new_user_name")

    def test_user_with_managed_permission_cannot_create_users(self):
        self.jam.iaso_profile.org_units.set([self.org_unit_from_parent_type.id])
        self.client.force_authenticate(self.jam)
        data = {
            "user_name": "unittest_user_name",
            "password": "unittest_password",
            "first_name": "unittest_first_name",
            "last_name": "unittest_last_name",
        }
        response = self.client.post(f"/api/profiles/", data=data, format="json")
        self.assertEqual(response.status_code, 403)

    def test_user_with_managed_permission_cannot_delete_users(self):
        self.jam.iaso_profile.org_units.set([self.org_unit_from_parent_type.id])
        self.client.force_authenticate(self.jam)
        jum = Profile.objects.get(user=self.jum)
        response = self.client.delete(f"/api/profiles/{jum.id}/")
        self.assertEqual(response.status_code, 403)

    def test_user_with_managed_permission_cannot_update_from_unmanaged_org_unit(self):
        self.jam.iaso_profile.org_units.set([self.child_org_unit.id])
        self.jum.iaso_profile.org_units.set([self.org_unit_from_sub_type.id])
        self.client.force_authenticate(self.jam)
        data = {
            "user_name": "unittest_user_name",
            "password": "unittest_password",
            "first_name": "unittest_first_name",
            "last_name": "unittest_last_name",
        }
        jum = Profile.objects.get(user=self.jum)
        response = self.client.patch(f"/api/profiles/{jum.id}/", data=data, format="json")
        self.assertEqual(response.status_code, 403)

    def test_update_user_add_phone_number(self):
        self.jam.iaso_profile.org_units.set([self.org_unit_from_parent_type.id])
        self.client.force_authenticate(self.john)
        jum = Profile.objects.get(user=self.jum)
        data = {
            "user_name": "unittest_user_name",
            "password": "unittest_password",
            "first_name": "unittest_first_name",
            "last_name": "unittest_last_name",
            "phone_number": "32477123456",
            "country_code": "be",
        }
        response = self.client.patch(f"/api/profiles/{jum.id}/", data=data, format="json")
        self.assertEqual(response.status_code, 200)
        updated_jum = Profile.objects.get(user=self.jum)
        self.assertEqual(updated_jum.phone_number.as_e164, "+32477123456")

        def test_update_user_with_malformed_phone_number(self):
            self.jam.iaso_profile.org_units.set([self.org_unit_from_parent_type.id])
            self.client.force_authenticate(self.jam)
            jum = Profile.objects.get(user=self.jum)
            data = {
                "user_name": "unittest_user_name",
                "password": "unittest_password",
                "first_name": "unittest_first_name",
                "last_name": "unittest_last_name",
                "phone_number": "not_a_phone_number",
                "country_code": "US",
            }
            response = self.client.patch(f"/api/profiles/{jum.id}/", data=data, format="json")
            self.assertNotEqual(response.status_code, 200)
            self.assertEqual(response.data["errorKey"], "phone_number")
            self.assertEqual(response.data["errorMessage"], _("Invalid phone number"))

    def test_update_user_projects(self):
        user = self.jam
        self.assertTrue(user.has_perm(permission.USERS_MANAGED))
        self.assertFalse(user.has_perm(permission.USERS_ADMIN))

        jum_profile = Profile.objects.get(user=self.jum)
        self.assertEqual(jum_profile.projects.count(), 1)
        self.assertEqual(jum_profile.projects.first(), self.project)

        self.client.force_authenticate(user)

        # Case 1.
        # Because `projects` is always sent by the front-end, modifying another value (here `user_name`)
        # should be allowed without touching `projects`.
        data = {
            "user_name": "jum_new_user_name",
            "projects": [self.project.id],
        }
        response = self.client.patch(f"/api/profiles/{jum_profile.id}/", data=data, format="json")
        self.assertEqual(response.status_code, 200)
        jum_profile.refresh_from_db()
        self.assertEqual(jum_profile.projects.count(), 1)
        self.assertEqual(jum_profile.projects.first(), self.project)
        self.assertEqual(jum_profile.user.username, "jum_new_user_name")

        # Case 2.
        # Changing `projects` should not be allowed for users without `permission._USERS_ADMIN`.
        new_project = m.Project.objects.create(name="New project", app_id="new.project", account=self.account)
        data = {
            "user_name": "jum_new_user_name",
            "projects": [new_project.id],
        }
        response = self.client.patch(f"/api/profiles/{jum_profile.id}/", data=data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"],
            "User with permission menupermissions.iaso_users_managed cannot change project attributions",
        )
        jum_profile.refresh_from_db()
        self.assertEqual(jum_profile.projects.count(), 1)
        self.assertEqual(jum_profile.projects.first(), self.project)

        # Case 3.
        # Changing `projects` should be allowed for users with `permission._USERS_ADMIN`.
        perm = Permission.objects.get(codename=permission._USERS_ADMIN)
        user.user_permissions.add(perm)
        del user._perm_cache
        del user._user_perm_cache
        self.assertTrue(user.has_perm(permission.USERS_ADMIN))
        data = {
            "user_name": "jum_new_user_name",
            "projects": [new_project.id],
        }
        response = self.client.patch(f"/api/profiles/{jum_profile.id}/", data=data, format="json")
        self.assertEqual(response.status_code, 200)
        jum_profile.refresh_from_db()
        self.assertEqual(jum_profile.projects.count(), 1)
        self.assertEqual(jum_profile.projects.first(), new_project)

    def get_new_user_data(self):
        user_name = "audit_user"
        pwd = "admin1234lol"
        first_name = "audit_user_first_name"
        last_name = "audit_user_last_name"
        email = "audit@test.com"
        organization = "Bluesquare"
        org_units = [
            {
                "id": f"{self.org_unit_from_parent_type.id}",
                "name": self.org_unit_from_parent_type.name,
                "validation_status": self.org_unit_from_parent_type.validation_status,
                "has_children": False,
                "org_unit_type_id": self.parent_org_unit_type.id,
                "org_unit_type_short_name": "Cnc",
            }
        ]
        language = "fr"
        home_page = "/forms/list"
        dhis2_id = "666666666666"
        user_roles = [self.user_role.id]
        user_roles_permissions = [
            {
                "id": self.user_role.id,
                "name": self.user_role.group.name,
                "permissions": [self.permission.name],
                "created_at": self.user_role.created_at,
                "updated_at": self.user_role.updated_at,
            }
        ]
        user_permissions = ["iaso_org_units_read"]
        send_email_invitation = False
        projects = [self.project.id]
        phone_number = "32475888888"
        country_code = "be"
        data = {
            "user_name": user_name,
            "password": pwd,
            "first_name": first_name,
            "last_name": last_name,
            "send_email_invitation": send_email_invitation,
            "email": email,
            "organization": organization,
            "language": language,
            "home_page": home_page,
            "dhis2_id": dhis2_id,
            "permissions": [],  # This looks legacy from an older version of the API
            "user_permissions": user_permissions,
            "projects": projects,
            "phone_number": phone_number,
            "country_code": country_code,
            "user_roles": user_roles,
            "user_roles_permissions": user_roles_permissions,
            "org_units": org_units,
        }
        return data

    def test_log_on_user_create(self):
        self.client.force_authenticate(self.john)

        data = self.get_new_user_data()
        response = self.client.post("/api/profiles/", data=data, format="json")
        response_data = self.assertJSONResponse(response, 200)
        new_profile_id = response_data["id"]
        new_user_id = response_data["user_id"]

        response = self.client.get(
            f"/api/logs/?contentType=iaso.profile&fields=past_value,new_value&objectId={new_profile_id}"
        )
        response_data = self.assertJSONResponse(response, 200)
        logs = response_data["list"]
        log = logs[0]

        try:
            jsonschema.validate(instance=log, schema=PROFILE_LOG_SCHEMA)
        except jsonschema.exceptions.ValidationError as ex:
            self.fail(msg=str(ex))

        self.assertEqual(log["past_value"], [])
        self.assertEqual(log["new_value"][0]["pk"], new_profile_id)
        new_profile = log["new_value"][0]["fields"]
        self.assertEqual(new_profile["user"], new_user_id)
        self.assertEqual(new_profile["username"], data["user_name"])
        self.assertEqual(new_profile["first_name"], data["first_name"])
        self.assertEqual(new_profile["last_name"], data["last_name"])
        self.assertEqual(new_profile["email"], data["email"])
        self.assertEqual(new_profile["organization"], data["organization"])
        self.assertEqual(len(new_profile["user_permissions"]), 1)
        self.assertEqual(new_profile["user_permissions"], data["user_permissions"])
        self.assertTrue(new_profile["password_updated"])
        self.assertNotIn("password", new_profile.keys())

        self.assertEqual(new_profile["dhis2_id"], data["dhis2_id"])
        self.assertEqual(new_profile["language"], data["language"])
        self.assertEqual(new_profile["home_page"], data["home_page"])
        self.assertEqual(new_profile["phone_number"], f'+{data["phone_number"]}')
        self.assertEqual(len(new_profile["org_units"]), 1)
        self.assertIn(self.org_unit_from_parent_type.id, new_profile["org_units"])
        self.assertEqual(len(new_profile["user_roles"]), 1)
        self.assertIn(self.user_role.id, new_profile["user_roles"])
        self.assertEqual(len(new_profile["projects"]), 1)
        self.assertIn(self.project.id, new_profile["projects"])

    def test_log_on_user_delete(self):
        self.client.force_authenticate(self.john)
        data = self.get_new_user_data()
        response = self.client.post("/api/profiles/", data=data, format="json")
        response_data = self.assertJSONResponse(response, 200)
        new_profile_id = response_data["id"]
        new_user_id = response_data["user_id"]

        response = self.client.delete(f"/api/profiles/{new_profile_id}/")
        self.assertJSONResponse(response, 200)

        response = self.client.get(
            f"/api/logs/?contentType=iaso.profile&fields=past_value,new_value&objectId={new_profile_id}"
        )
        response_data = self.assertJSONResponse(response, 200)
        logs = response_data["list"]
        log = logs[0]

        try:
            jsonschema.validate(instance=log, schema=PROFILE_LOG_SCHEMA)
        except jsonschema.exceptions.ValidationError as ex:
            self.fail(msg=str(ex))

        self.assertEqual(log["new_value"][0]["pk"], new_profile_id)
        new_profile = log["new_value"][0]["fields"]
        self.assertEqual(new_profile["user"], new_user_id)
        self.assertEqual(new_profile["username"], data["user_name"])
        self.assertEqual(new_profile["first_name"], data["first_name"])
        self.assertEqual(new_profile["last_name"], data["last_name"])
        self.assertEqual(new_profile["email"], data["email"])
        self.assertEqual(len(new_profile["user_permissions"]), 1)
        self.assertEqual(new_profile["user_permissions"], data["user_permissions"])
        self.assertIsNotNone(new_profile["deleted_at"])
        self.assertFalse(new_profile["password_updated"])
        self.assertNotIn("password", new_profile.keys())

        self.assertEqual(new_profile["dhis2_id"], data["dhis2_id"])
        self.assertEqual(new_profile["language"], data["language"])
        self.assertEqual(new_profile["home_page"], data["home_page"])
        self.assertEqual(new_profile["phone_number"], f'+{data["phone_number"]}')
        self.assertEqual(len(new_profile["org_units"]), 1)
        self.assertIn(self.org_unit_from_parent_type.id, new_profile["org_units"])
        self.assertEqual(len(new_profile["user_roles"]), 1)
        self.assertIn(self.user_role.id, new_profile["user_roles"])
        self.assertEqual(len(new_profile["projects"]), 1)
        self.assertIn(self.project.id, new_profile["projects"])
        self.assertIsNotNone(new_profile["deleted_at"])

        self.assertEqual(log["past_value"][0]["pk"], new_profile_id)
        past_profile = log["past_value"][0]["fields"]
        self.assertEqual(past_profile["user"], new_user_id)
        self.assertEqual(past_profile["username"], data["user_name"])
        self.assertEqual(past_profile["first_name"], data["first_name"])
        self.assertEqual(past_profile["last_name"], data["last_name"])
        self.assertEqual(past_profile["email"], data["email"])
        self.assertEqual(len(past_profile["user_permissions"]), 1)
        self.assertEqual(past_profile["user_permissions"], data["user_permissions"])
        self.assertIsNone(past_profile["deleted_at"])
        self.assertNotIn("password", past_profile.keys())

        self.assertEqual(past_profile["dhis2_id"], data["dhis2_id"])
        self.assertEqual(past_profile["language"], data["language"])
        self.assertEqual(past_profile["home_page"], data["home_page"])
        self.assertEqual(past_profile["phone_number"], f'+{data["phone_number"]}')
        self.assertEqual(len(past_profile["org_units"]), 1)
        self.assertIn(self.org_unit_from_parent_type.id, past_profile["org_units"])
        self.assertEqual(len(past_profile["user_roles"]), 1)
        self.assertIn(self.user_role.id, past_profile["user_roles"])
        self.assertEqual(len(past_profile["projects"]), 1)
        self.assertIn(self.project.id, past_profile["projects"])
        self.assertIsNone(past_profile["deleted_at"])

    def test_log_on_user_update(self):
        self.client.force_authenticate(self.john)
        data = self.get_new_user_data()
        response = self.client.post("/api/profiles/", data=data, format="json")
        response_data = self.assertJSONResponse(response, 200)
        new_profile_id = response_data["id"]
        new_user_id = response_data["user_id"]
        new_user_name = response_data["user_name"]

        new_data = {
            "id": new_profile_id,
            "user_name": new_user_name,
            "org_units": [
                {
                    "id": f"{self.org_unit_from_parent_type.id}",
                    "name": self.org_unit_from_parent_type.name,
                    "validation_status": self.org_unit_from_parent_type.validation_status,
                    "has_children": False,
                    "org_unit_type_id": self.parent_org_unit_type.id,
                    "org_unit_type_short_name": "Cnc",
                },
                {
                    "id": f"{self.org_unit_from_sub_type.id}",
                    "name": self.org_unit_from_sub_type.name,
                    "validation_status": self.org_unit_from_sub_type.validation_status,
                    "has_children": False,
                    "org_unit_type_id": self.sub_unit_type.id,
                    "org_unit_type_short_name": "Jds",
                },
            ],
            "language": "en",
            "password": "yolo",
            "home_page": "/orgunits/list",
            "organization": "Bluesquare",
            "user_permissions": ["iaso_org_units_read", "iaso_forms"],
            "user_roles": [],
            "user_roles_permissions": [],
        }

        response = self.client.patch(f"/api/profiles/{new_profile_id}/", data=new_data, format="json")
        self.assertJSONResponse(response, 200)

        response = self.client.get(
            f"/api/logs/?contentType=iaso.profile&fields=past_value,new_value&objectId={new_profile_id}"
        )
        response_data = self.assertJSONResponse(response, 200)
        logs = response_data["list"]
        log = logs[0]

        try:
            jsonschema.validate(instance=log, schema=PROFILE_LOG_SCHEMA)
        except jsonschema.exceptions.ValidationError as ex:
            self.fail(msg=str(ex))
        self.assertEqual(log["past_value"][0]["pk"], new_profile_id)
        past_value = log["past_value"][0]["fields"]
        self.assertEqual(past_value["user"], new_user_id)
        self.assertEqual(past_value["username"], data["user_name"])
        self.assertEqual(past_value["first_name"], data["first_name"])
        self.assertEqual(past_value["last_name"], data["last_name"])
        self.assertEqual(past_value["email"], data["email"])
        self.assertEqual(len(past_value["user_permissions"]), 1)
        self.assertEqual(past_value["user_permissions"], data["user_permissions"])
        self.assertNotIn("password", past_value.keys())

        self.assertEqual(past_value["dhis2_id"], data["dhis2_id"])
        self.assertEqual(past_value["language"], data["language"])
        self.assertEqual(past_value["home_page"], data["home_page"])
        self.assertEqual(past_value["phone_number"], f'+{data["phone_number"]}')
        self.assertEqual(len(past_value["org_units"]), 1)
        self.assertIn(
            self.org_unit_from_parent_type.id,
            past_value["org_units"],
        )
        self.assertEqual(len(past_value["user_roles"]), 1)
        self.assertIn(self.user_role.id, past_value["user_roles"])
        self.assertEqual(len(past_value["projects"]), 1)
        self.assertIn(self.project.id, past_value["projects"])
        self.assertEqual(log["new_value"][0]["pk"], new_profile_id)
        new_value = log["new_value"][0]["fields"]
        self.assertTrue(new_value["password_updated"])
        self.assertNotIn("password", new_value.keys())
        self.assertEqual(len(new_value["user_permissions"]), 2)
        self.assertIn("iaso_forms", new_value["user_permissions"])
        self.assertIn("iaso_org_units_read", new_value["user_permissions"])
        self.assertEqual(new_value["language"], new_data["language"])
        self.assertEqual(new_value["home_page"], new_data["home_page"])
        self.assertEqual(new_value["organization"], new_data["organization"])
        self.assertEqual(len(new_value["org_units"]), 2)
        self.assertIn(self.org_unit_from_parent_type.id, new_value["org_units"])
        self.assertIn(self.org_unit_from_sub_type.id, new_value["org_units"])
        self.assertEqual(new_value["user_roles"], [])

    def test_log_on_user_updates_own_profile(self):
        self.client.force_authenticate(self.jim)
        new_data = {"language": "fr"}
        response = self.client.patch(f"/api/profiles/me/", data=new_data, format="json")
        self.assertJSONResponse(response, 200)
        # Log as super user to access the logs API
        self.client.force_authenticate(self.john)
        response = self.client.get(
            f"/api/logs/?contentType=iaso.profile&fields=past_value,new_value&objectId={self.jim.iaso_profile.id}"
        )
        response_data = self.assertJSONResponse(response, 200)
        logs = response_data["list"]
        log = logs[0]

        try:
            jsonschema.validate(instance=log, schema=PROFILE_LOG_SCHEMA)
        except jsonschema.exceptions.ValidationError as ex:
            self.fail(msg=str(ex))

        self.assertEqual(log["past_value"][0]["pk"], self.jim.iaso_profile.id)
        past_value = log["past_value"][0]["fields"]
        self.assertEqual(past_value["user"], self.jim.id)
        self.assertEqual(past_value["username"], self.jim.username)
        self.assertEqual(past_value["first_name"], "")
        self.assertEqual(past_value["language"], None)
        self.assertNotIn("password", past_value.keys())

        self.assertEqual(log["new_value"][0]["pk"], self.jim.iaso_profile.id)
        new_value = log["new_value"][0]["fields"]
        self.assertEqual(new_value["user"], self.jim.id)
        self.assertEqual(new_value["username"], self.jim.username)
        self.assertEqual(new_value["first_name"], "")
        self.assertEqual(new_value["language"], "fr")
        self.assertNotIn("password", new_value.keys())
