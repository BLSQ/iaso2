import datetime
import jsonschema
import pytz
from hat.audit.models import Modification
from iaso.test import APITestCase
from hat.menupermissions.constants import MODULES
from iaso import models as m
from django.contrib.contenttypes.models import ContentType
from hat.menupermissions import models as permission
from unittest.mock import patch

user_schema = {
    "type": "object",
    "properties": {
        "user_id": {"type": "number"},
        "username": {"type": "string"},
        "first_name": {"type": "string"},
        "last_name": {"type": "string"},
    },
    "required": ["user_id", "username", "first_name", "last_name"],
}

location = {
    "type": "object",
    "properties": {"id": {"type": "number"}, "name": {"type": "string"}},
    "required": ["id", "name"],
}

PROFILE_LOG_LIST_SCHEMA = {
    "type": "object",
    "properties": {
        "count": {"type": "number"},
        "page": {"type": "number"},
        "pages": {"type": "number"},
        "limit": {"type": "number"},
        "has_previous": {"type": "boolean"},
        "has_next": {"type": "boolean"},
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "number"},
                    "created_at": {"type": "string"},
                    "user": user_schema,
                    "modified_by": user_schema,
                    "past_location": {"type": "array", "items": location, "minContains": 0},
                    "new_location": {"type": "array", "items": location, "minContains": 0},
                    "fields_modified": {"type": "array", "items": {"type": "string"}, "minContains": 0},
                },
                "required": [
                    "id",
                    "user",
                    "modified_by",
                    "past_location",
                    "new_location",
                    "fields_modified",
                    "created_at",
                ],
            },
        },
    },
    "required": ["count", "results", "has_next", "has_previous", "pages", "page", "limit"],
}


class ProfileLogsTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.MODULES = [module["codename"] for module in MODULES]
        cls.account = m.Account.objects.create(name="Main account", modules=cls.MODULES)
        cls.other_account = m.Account.objects.create(name="Other account")
        cls.project_1 = m.Project.objects.create(
            name="Project 1",
            app_id="test.app.id",
            account=cls.account,
        )
        cls.project_2 = m.Project.objects.create(
            name="Project 2",
            app_id="test.app.id",
            account=cls.account,
        )
        source = m.DataSource.objects.create(name="Main data source")
        source.projects.add(cls.project_1)
        source.projects.add(cls.project_2)
        cls.source = source
        cls.org_unit_type = m.OrgUnitType.objects.create(name="Org Unit Type", short_name="outype")
        cls.version_1 = m.SourceVersion.objects.create(data_source=cls.source, number=1)
        cls.account.default_version = cls.version_1
        cls.account.save()

        cls.org_unit_1 = m.OrgUnit.objects.create(
            org_unit_type=cls.org_unit_type,
            version=cls.version_1,
            name="Org unit 1",
            validation_status=m.OrgUnit.VALIDATION_VALID,
            source_ref="FooBarB4z00",
        )
        cls.org_unit_2 = m.OrgUnit.objects.create(
            org_unit_type=cls.org_unit_type,
            version=cls.version_1,
            name="Org unit 2",
            validation_status=m.OrgUnit.VALIDATION_VALID,
            source_ref="FooBarB4z00",
        )
        # Users.
        cls.user_with_permission_1 = cls.create_user_with_profile(
            username="janedoe", account=cls.account, permissions=[permission._USERS_ADMIN]
        )
        cls.user_with_permission_2 = cls.create_user_with_profile(
            username="bordoe", account=cls.account, permissions=[permission._USERS_ADMIN]
        )
        cls.user_without_permission = cls.create_user_with_profile(
            username="jim", account=cls.account, permissions=[permission._FORMS]
        )
        cls.edited_user_1 = cls.create_user_with_profile(
            username="jam",
            account=cls.account,
            permissions=[permission._USERS_MANAGED],
            language="en",
        )
        cls.edited_user_2 = cls.create_user_with_profile(
            username="jom", account=cls.account, permissions=[], language="fr"
        )
        cls.content_type = ContentType.objects.get(
            app_label="iaso",
            model="profile",
        )
        date1 = datetime.datetime(2020, 2, 10, 0, 0, 5, tzinfo=pytz.UTC)
        date2 = datetime.datetime(2020, 2, 15, 0, 0, 5, tzinfo=pytz.UTC)
        # date3 = datetime.datetime(2020, 2, 15, 0, 0, 5, tzinfo=pytz.UTC)
        # Logs
        # by user 1 for editabe user 1 with org unit 1 before date
        with patch("django.utils.timezone.now", lambda: date1):
            cls.log_1 = Modification.objects.create(
                user=cls.user_with_permission_1,
                object_id=str(cls.edited_user_1.iaso_profile.id),
                source="API",
                content_type=cls.content_type,
                past_value=[
                    {
                        "pk": cls.edited_user_1.iaso_profile.id,
                        "fields": {
                            "user": cls.edited_user_1.id,
                            "email": "",
                            "dhis2_id": "12345",
                            "account": cls.account.id,
                            "language": "fr",
                            "projects": [cls.project_1.id],
                            "org_units": [cls.org_unit_1.id],
                            "user_roles": [],
                            "user_permissions": ["iaso_fictional_permission"],
                            "phone_number": "+32485996633",
                            "username": cls.edited_user_1.username,
                            "first_name": "Ali",
                            "last_name": "G",
                            "deleted_at": None,
                            "home_page": "",
                        },
                    }
                ],
                new_value=[
                    {
                        "pk": cls.edited_user_1.iaso_profile.id,
                        "fields": {
                            "user": cls.edited_user_1.id,
                            "email": "",
                            "dhis2_id": "12345",
                            "account": cls.account.id,
                            "language": "fr",
                            "projects": [cls.project_1.id],
                            "user_roles": [],
                            "org_units": [cls.org_unit_1.id],
                            "user_permissions": ["iaso_fictional_permission"],
                            "phone_number": "+32485996633",
                            "username": cls.edited_user_1.username,
                            "first_name": "Sacha",  # Changed
                            "last_name": "Baron Cohen",  # Changed
                            "deleted_at": None,
                            "home_page": "",
                            "password_updated": True,  # Changed
                        },
                    }
                ],
            )
        # by user 1 for editabe user 1 with org unit 1 after date
        with patch("django.utils.timezone.now", lambda: date2):
            cls.log_2 = Modification.objects.create(
                user=cls.user_with_permission_1,
                object_id=str(cls.edited_user_1.iaso_profile.id),
                source="API",
                content_type=cls.content_type,
                past_value=[
                    {
                        "pk": cls.edited_user_1.iaso_profile.id,
                        "fields": {
                            "user": cls.edited_user_1.id,
                            "email": "",
                            "dhis2_id": "12345",
                            "account": cls.account.id,
                            "language": "fr",
                            "projects": [cls.project_1.id],
                            "org_units": [cls.org_unit_1.id],
                            "user_roles": [],
                            "user_permissions": ["iaso_fictional_permission"],
                            "phone_number": "+32485996633",
                            "username": cls.edited_user_1.username,
                            "first_name": "Sacha",
                            "last_name": "Baron Cohen",
                            "deleted_at": None,
                            "home_page": "",
                        },
                    }
                ],
                new_value=[
                    {
                        "pk": cls.edited_user_1.iaso_profile.id,
                        "fields": {
                            "user": cls.edited_user_1.id,
                            "email": "",
                            "dhis2_id": "12345",
                            "account": cls.account.id,
                            "language": "fr",
                            "projects": [cls.project_1.id],
                            "user_roles": [],
                            "org_units": [cls.org_unit_1.id],
                            "user_permissions": ["iaso_fictional_permission"],
                            "phone_number": "+32485996633",
                            "username": cls.edited_user_1.username,
                            "first_name": "Mel",  # Changed
                            "last_name": "Brooks",  # Changed
                            "deleted_at": None,
                            "home_page": "",
                            "password_updated": True,  # Changed
                        },
                    }
                ],
            )
        # by user 1 for editable user 2 with org unit 2 before date
        with patch("django.utils.timezone.now", lambda: date1):
            cls.log_3 = Modification.objects.create(
                user=cls.user_with_permission_1,
                object_id=str(cls.edited_user_1.iaso_profile.id),
                source="API",
                content_type=cls.content_type,
                past_value=[
                    {
                        "pk": cls.edited_user_2.iaso_profile.id,
                        "fields": {
                            "user": cls.edited_user_2.id,
                            "email": "",
                            "dhis2_id": "12345",
                            "account": cls.account.id,
                            "language": "fr",
                            "projects": [cls.project_1.id],
                            "org_units": [cls.org_unit_1.id],
                            "user_roles": [],
                            "user_permissions": ["iaso_fictional_permission"],
                            "phone_number": "+32485996633",
                            "username": cls.edited_user_2.username,
                            "first_name": "Sacha",
                            "last_name": "Baron Cohen",
                            "deleted_at": None,
                            "home_page": "",
                        },
                    }
                ],
                new_value=[
                    {
                        "pk": cls.edited_user_2.iaso_profile.id,
                        "fields": {
                            "user": cls.edited_user_2.id,
                            "email": "",
                            "dhis2_id": "12345",
                            "account": cls.account.id,
                            "language": "fr",
                            "projects": [cls.project_1.id],
                            "user_roles": [],
                            "org_units": [cls.org_unit_2.id],  # Changed
                            "user_permissions": ["iaso_fictional_permission"],
                            "phone_number": "+32485996633",
                            "username": cls.edited_user_2.username,
                            "first_name": "Mel",  # Changed
                            "last_name": "Brooks",  # Changed
                            "deleted_at": None,
                            "home_page": "",
                            "password_updated": True,  # Changed
                        },
                    }
                ],
                created_at=date1,
            )
        # by user 2 for editable user 1 with org unit 2 before date
        with patch("django.utils.timezone.now", lambda: date1):
            cls.log_4 = Modification.objects.create(
                user=cls.user_with_permission_2,
                object_id=str(cls.edited_user_1.iaso_profile.id),
                source="API",
                content_type=cls.content_type,
                past_value=[
                    {
                        "pk": cls.edited_user_1.iaso_profile.id,
                        "fields": {
                            "user": cls.edited_user_1.id,
                            "email": "",
                            "dhis2_id": "12345",
                            "account": cls.account.id,
                            "language": "fr",
                            "projects": [cls.project_1.id],
                            "org_units": [cls.org_unit_2.id],
                            "user_roles": [],
                            "user_permissions": ["iaso_fictional_permission"],
                            "phone_number": "+32485996633",
                            "username": cls.edited_user_1.username,
                            "first_name": "Johnny",
                            "last_name": "Cage",
                            "deleted_at": None,
                            "home_page": "",
                        },
                    }
                ],
                new_value=[
                    {
                        "pk": cls.edited_user_1.iaso_profile.id,
                        "fields": {
                            "user": cls.edited_user_1.id,
                            "email": "",
                            "dhis2_id": "12345",
                            "account": cls.account.id,
                            "language": "fr",
                            "projects": [cls.project_1.id],
                            "user_roles": [],
                            "org_units": [cls.org_unit_2.id],
                            "user_permissions": ["iaso_fictional_permission"],
                            "phone_number": "+32485996633",
                            "username": cls.edited_user_1.username,
                            "first_name": "Liu",  # Changed
                            "last_name": "Kang",  # Changed
                            "deleted_at": None,
                            "home_page": "",
                            "password_updated": True,  # Changed
                        },
                    }
                ],
            )
        # by user 2 for editable user 1 with org unit 2 after date
        with patch("django.utils.timezone.now", lambda: date2):
            cls.log_5 = Modification.objects.create(
                user=cls.user_with_permission_2,
                object_id=str(cls.edited_user_1.iaso_profile.id),
                source="API",
                content_type=cls.content_type,
                past_value=[
                    {
                        "pk": cls.edited_user_1.iaso_profile.id,
                        "fields": {
                            "user": cls.edited_user_1.id,
                            "email": "",
                            "dhis2_id": "12345",
                            "account": cls.account.id,
                            "language": "fr",
                            "projects": [cls.project_1.id],
                            "org_units": [cls.org_unit_2.id],
                            "user_roles": [],
                            "user_permissions": ["iaso_fictional_permission"],
                            "phone_number": "+32485996633",
                            "username": cls.edited_user_1.username,
                            "first_name": "Shao",
                            "last_name": "Kahn",
                            "deleted_at": None,
                            "home_page": "",
                        },
                    }
                ],
                new_value=[
                    {
                        "pk": cls.edited_user_1.iaso_profile.id,
                        "fields": {
                            "user": cls.edited_user_1.id,
                            "email": "",
                            "dhis2_id": "12345",
                            "account": cls.account.id,
                            "language": "fr",
                            "projects": [cls.project_1.id],
                            "user_roles": [],
                            "org_units": [cls.org_unit_1.id],  # Changed
                            "user_permissions": ["iaso_fictional_permission"],
                            "phone_number": "+32485996633",
                            "username": cls.edited_user_1.username,
                            "first_name": "Shang",  # Changed
                            "last_name": "Tsung",  # Changed
                            "deleted_at": None,
                            "home_page": "",
                            "password_updated": True,  # Changed
                        },
                    }
                ],
            )
        # by user 2 for editable user 2 with org unit 1 after date
        with patch("django.utils.timezone.now", lambda: date2):
            cls.log_6 = Modification.objects.create(
                user=cls.user_with_permission_2,
                object_id=str(cls.edited_user_1.iaso_profile.id),
                source="API",
                content_type=cls.content_type,
                past_value=[
                    {
                        "pk": cls.edited_user_2.iaso_profile.id,
                        "fields": {
                            "user": cls.edited_user_2.id,
                            "email": "",
                            "dhis2_id": "12345",
                            "account": cls.account.id,
                            "language": "fr",
                            "projects": [cls.project_1.id],
                            "org_units": [cls.org_unit_1.id],
                            "user_roles": [],
                            "user_permissions": ["iaso_fictional_permission"],
                            "phone_number": "+32485996633",
                            "username": cls.edited_user_2.username,
                            "first_name": "",
                            "last_name": "",
                            "deleted_at": None,
                            "home_page": "",
                        },
                    }
                ],
                new_value=[
                    {
                        "pk": cls.edited_user_2.iaso_profile.id,
                        "fields": {
                            "user": cls.edited_user_2.id,
                            "email": "",
                            "dhis2_id": "12345",
                            "account": cls.account.id,
                            "language": "fr",
                            "projects": [cls.project_1.id],
                            "user_roles": [],
                            "org_units": [cls.org_unit_1.id],
                            "user_permissions": ["iaso_fictional_permission"],
                            "phone_number": "+32485996633",
                            "username": cls.edited_user_2.username,
                            "first_name": "Kung",  # Changed
                            "last_name": "Lao",  # Changed
                            "deleted_at": None,
                            "home_page": "",
                            "password_updated": False,
                        },
                    }
                ],
            )

    def test_unauthenticated_user(self):
        """GET /api/userlogs/ anonymous user --> 401"""
        response = self.client.get("/api/userlogs/")
        self.assertJSONResponse(response, 401)

    def test_user_no_permission(self):
        """GET /api/userlogs/ without USERS_ADMIN permission --> 403"""
        self.client.force_authenticate(self.user_without_permission)
        response = self.client.get("/api/userlogs/")
        self.assertJSONResponse(response, 403)

    def test_results_filtered_by_account(self):
        pass

    def test_get_list(self):
        """GET /api/userlogs/ with USERS_ADMIN permission - golden path"""
        self.client.force_authenticate(self.user_with_permission_1)
        response = self.client.get("/api/userlogs/")
        data = self.assertJSONResponse(response, 200)
        self.assertEquals(data["count"], 6)
        try:
            jsonschema.validate(instance=data, schema=PROFILE_LOG_LIST_SCHEMA)
        except jsonschema.exceptions.ValidationError as ex:
            self.fail(msg=str(ex))

    def test_filters(self):
        """GET /api/userlogs/ with USERS_ADMIN permission
        Test filters on users, modified by, location and dates"

        """
        self.client.force_authenticate(self.user_with_permission_1)
        response = self.client.get(f"/api/userlogs/?user_ids={self.edited_user_1.id}")
        data = self.assertJSONResponse(response, 200)
        self.assertEquals(data["count"], 4)
        try:
            jsonschema.validate(instance=data, schema=PROFILE_LOG_LIST_SCHEMA)
        except jsonschema.exceptions.ValidationError as ex:
            self.fail(msg=str(ex))

        response = self.client.get(
            f"/api/userlogs/?user_ids={self.edited_user_1.id}&modified_by={self.user_with_permission_1.id}"
        )
        data = self.assertJSONResponse(response, 200)
        self.assertEquals(data["count"], 2)
        try:
            jsonschema.validate(instance=data, schema=PROFILE_LOG_LIST_SCHEMA)
        except jsonschema.exceptions.ValidationError as ex:
            self.fail(msg=str(ex))

        response = self.client.get(f"/api/userlogs/?user_ids={self.edited_user_1.id}&org_unit_id={self.org_unit_2.id}")
        data = self.assertJSONResponse(response, 200)
        self.assertEquals(data["count"], 2)
        try:
            jsonschema.validate(instance=data, schema=PROFILE_LOG_LIST_SCHEMA)
        except jsonschema.exceptions.ValidationError as ex:
            self.fail(msg=str(ex))

        response = self.client.get(
            f"/api/userlogs/?user_ids={self.edited_user_1.id}&modified_by={self.user_with_permission_1.id}&created_at_before=2020-02-14"
        )
        data = self.assertJSONResponse(response, 200)
        self.assertEquals(data["count"], 1)
        try:
            jsonschema.validate(instance=data, schema=PROFILE_LOG_LIST_SCHEMA)
        except jsonschema.exceptions.ValidationError as ex:
            self.fail(msg=str(ex))

        response = self.client.get(
            f"/api/userlogs/?user_ids={self.edited_user_1.id}&modified_by={self.user_with_permission_1.id}&created_at_after=2020-02-14"
        )
        data = self.assertJSONResponse(response, 200)
        self.assertEquals(data["count"], 1)
        try:
            jsonschema.validate(instance=data, schema=PROFILE_LOG_LIST_SCHEMA)
        except jsonschema.exceptions.ValidationError as ex:
            self.fail(msg=str(ex))

        results = data["results"]
        self.assertEquals(len(results), 1)
        user = results[0]["user"]
        self.assertEquals(user["id"], self.edited_user_1.iaso_profile.id)
        self.assertEquals(user["user_id"], self.edited_user_1.id)
        self.assertEquals(user["username"], self.edited_user_1.username)
        self.assertEquals(user["first_name"], self.edited_user_1.first_name)
        self.assertEquals(user["last_name"], self.edited_user_1.last_name)
        modified_by = results[0]["modified_by"]
        self.assertEquals(modified_by["id"], self.user_with_permission_1.iaso_profile.id)
        self.assertEquals(modified_by["user_id"], self.user_with_permission_1.id)
        self.assertEquals(modified_by["username"], self.user_with_permission_1.username)
        self.assertEquals(modified_by["first_name"], self.user_with_permission_1.first_name)
        self.assertEquals(modified_by["last_name"], self.user_with_permission_1.last_name)
        past_location = results[0]["past_location"][0]
        self.assertEquals(past_location["name"], self.org_unit_1.name)
        self.assertEquals(past_location["id"], self.org_unit_1.id)
        new_location = results[0]["new_location"][0]
        self.assertEquals(new_location["name"], self.org_unit_1.name)
        self.assertEquals(new_location["id"], self.org_unit_1.id)

        response = self.client.get(
            f"/api/userlogs/?user_ids={self.edited_user_1.id}&modified_by={self.user_with_permission_1.id}&created_at_after=2020-02-14&created_at_before=2020-02-09"
        )
        data = self.assertJSONResponse(response, 200)
        self.assertEquals(data["count"], 0)
        try:
            jsonschema.validate(instance=data, schema=PROFILE_LOG_LIST_SCHEMA)
        except jsonschema.exceptions.ValidationError as ex:
            self.fail(msg=str(ex))

        results = data["results"]
        self.assertEquals(results, [])
