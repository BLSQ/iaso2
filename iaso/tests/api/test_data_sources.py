from iaso import models as m
from iaso.test import APITestCase


class DataSourcesAPITestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.account, cls.data_source, cls.source_version, cls.project = cls.create_account_datasource_version_project(
            source_name="Data source", account_name="Global Health Initiative", project_name="Data collection"
        )
        _, cls.data_source2, cls.source_version2, cls.project2 = cls.create_account_datasource_version_project(
            source_name="Pyramid", account_name="Important Health Player", project_name="Campaign"
        )
        cls.project2.account = cls.account
        cls.data_source2.account = cls.account
        cls.project2.save()
        cls.data_source2.save()
        # read perms
        cls.jane = cls.create_user_with_profile(username="janedoe", account=cls.account, permissions=["iaso_mappings"])
        # write perms
        cls.joe = cls.create_user_with_profile(username="joe", account=cls.account, permissions=["iaso_write_sources"])
        # no perms
        cls.jim = cls.create_user_with_profile(username="jimdoe", account=cls.account)
        # with read but no write perms
        cls.john = cls.create_user_with_profile(username="johnny", account=cls.account, permissions=["iaso_sources"])

    def test_datasource_list_without_auth(self):
        """GET /datasources/ without auth should result in a 401"""

        response = self.client.get("/api/datasources/")
        self.assertJSONResponse(response, 401)

    def test_datasource_list_with_auth_no_permissions(self):
        """GET /projects/ with auth should result in a 403 as no permission"""
        self.client.force_authenticate(self.jim)

        response = self.client.get("/api/datasources/")
        self.assertJSONResponse(response, 403)

    def test_datasource_list_with_auth_ok(self):
        """GET /datasource/ with auth should result in a 200"""
        # if the user has one perms
        self.client.force_authenticate(self.jane)

        response = self.client.get("/api/datasources/")
        self.assertJSONResponse(response, 200)

    def test_datasource_post_with_all_params(self):
        """POST /datasource/ with all params should work OK"""
        self.client.force_authenticate(self.joe)

        response = self.client.post(
            "/api/datasources/",
            format="json",
            data={
                "name": "test_name",
                "read_only": True,
                "description": "test_description",
                "credentials": {
                    "dhis_name": "test_name",
                    "dhis_login": "test_login",
                    "dhis_url": "test_url",
                    "dhis_password": "test_password",
                },
                "project_ids": [self.project.pk],
            },
        )

        self.assertJSONResponse(response, 201)

    def test_datasource_post_without_credentials(self):
        """POST /datasource/ without credentials should NOT fail"""
        self.client.force_authenticate(self.joe)

        response = self.client.post(
            "/api/datasources/",
            format="json",
            data={
                "name": "test_name",
                "read_only": True,
                "description": "test_description",
                "project_ids": [self.project.pk],
            },
        )
        self.assertJSONResponse(response, 201)

    def test_datasource_post_without_project_ids(self):
        """POST /datasource/ without project_ids should NOT fail"""
        self.client.force_authenticate(self.joe)

        response = self.client.post(
            "/api/datasources/",
            format="json",
            data={
                "name": "test_name",
                "read_only": True,
                "description": "test_description",
                "credentials": {
                    "dhis_name": "test_name",
                    "dhis_login": "test_login",
                    "dhis_url": "test_url",
                    "dhis_password": "test_password",
                },
            },
        )
        self.assertJSONResponse(response, 201)

    def test_datasource_put_with_read_but_no_write_perms(self):
        """Can not create the data source with no write permission"""

        self.client.force_authenticate(self.john)
        response = self.client.post(
            "/api/datasources/",
            format="json",
            data={
                "name": "test_name",
                "read_only": True,
                "description": "test_description",
                "project_ids": [self.project.id],
                "credentials": {
                    "dhis_name": "test_name",
                    "dhis_login": "test_login",
                    "dhis_url": "test_url",
                    "dhis_password": "test_password",
                },
            },
        )
        self.assertJSONResponse(response, 403)

    def test_datasource_create_delete_fail_ok(self):
        """Create, read, delete fail, delete ok"""

        self.client.force_authenticate(self.joe)
        response = self.client.post(
            "/api/datasources/",
            format="json",
            data={
                "name": "test_name",
                "read_only": True,
                "description": "test_description",
                "project_ids": [self.project.id],
                "credentials": {
                    "dhis_name": "test_name",
                    "dhis_login": "test_login",
                    "dhis_url": "test_url",
                    "dhis_password": "test_password",
                },
            },
        )
        j = self.assertJSONResponse(response, 201)

        source_id = j["id"]
        response = self.client.get(f"/api/datasources/{source_id}/")
        j = self.assertJSONResponse(response, 200)
        self.assertEqual(j["name"], "test_name")

        # read but not write
        self.client.force_authenticate(self.jane)
        response = self.client.get(f"/api/datasources/{source_id}/")
        self.assertJSONResponse(response, 200)
        response = self.client.delete(f"/api/datasources/{source_id}/")
        self.assertJSONResponse(response, 403)

        # user with write
        self.client.force_authenticate(self.joe)
        response = self.client.delete(f"/api/datasources/{source_id}/")
        self.assertJSONResponse(response, 403)
        self.assertEqual(m.DataSource.objects.filter(id=source_id).count(), 1)

        response = self.client.get(f"/api/datasources/{source_id}/")
        self.assertJSONResponse(response, 200)

    def test_datasource_filters(self):
        self.client.force_authenticate(self.joe)

        response = self.client.get("/api/datasources/?name=Data")
        data = self.assertJSONResponse(response, 200)
        self.assertEqual(len(data["sources"]), 1)
        self.assertEqual(data["sources"][0]["id"], self.data_source.pk)
        response = self.client.get("/api/datasources/?name=Pyra")
        data = self.assertJSONResponse(response, 200)
        self.assertEqual(len(data["sources"]), 1)
        self.assertEqual(data["sources"][0]["id"], self.data_source2.pk)
        response = self.client.get(f"/api/datasources/?project_ids={self.project.pk}")
        data = self.assertJSONResponse(response, 200)
        self.assertEqual(len(data["sources"]), 1)
        self.assertEqual(data["sources"][0]["id"], self.data_source.pk)
