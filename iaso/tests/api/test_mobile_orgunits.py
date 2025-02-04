import time_machine

from django.contrib.gis.geos import Polygon, MultiPolygon, Point
from django.core.cache import cache

from iaso.api.query_params import APP_ID, LIMIT, PAGE, IDS
from iaso.models import (
    Account,
    DataSource,
    FeatureFlag,
    Form,
    FormVersion,
    Group,
    Instance,
    OrgUnit,
    OrgUnitReferenceInstance,
    OrgUnitType,
    Project,
    SourceVersion,
)
from iaso.test import APITestCase

BASE_URL = "/api/mobile/orgunits/"
BOUNDINGXBOX_URL = "/api/mobile/orgunits/boundingbox/"
BASE_APP_ID = "dragon.ball.saiyans"


class MobileOrgUnitAPITestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.account = account = Account.objects.create(name="Dragon Ball")
        cls.account2 = account2 = Account.objects.create(name="Saint Seiya")
        cls.project = project = Project.objects.create(
            name="Saiyans",
            app_id=BASE_APP_ID,
            account=account,
            needs_authentication=True,
        )
        cls.user = user = cls.create_user_with_profile(username="user", account=account, permissions=["iaso_org_units"])
        cls.user2 = cls.create_user_with_profile(username="user2", account=account2, permissions=["iaso_org_units"])
        cls.sw_source = sw_source = DataSource.objects.create(name="Vegeta Planet")
        sw_source.projects.add(project)
        cls.sw_version_1 = sw_version_1 = SourceVersion.objects.create(data_source=sw_source, number=1)
        cls.sw_version_2 = sw_version_2 = SourceVersion.objects.create(data_source=sw_source, number=2)
        sw_version = sw_version_2
        account.default_version = sw_version
        account.save()

        cls.group_1 = Group.objects.create(name="Old parent", source_version=sw_version_1)
        cls.group_2 = group_2 = Group.objects.create(name="Parent", source_version=sw_version_2)

        cls.warriors = warriors = OrgUnitType.objects.create(name="Warriors")
        warriors.projects.add(project)

        cls.super_saiyans = super_saiyans = OrgUnitType.objects.create(name="Super Saiyans")
        super_saiyans.projects.add(project)
        warriors.sub_unit_types.add(super_saiyans)

        cls.on_earth = on_earth = OrgUnitType.objects.create(name="Born on Earth")
        on_earth.projects.add(project)
        super_saiyans.sub_unit_types.add(on_earth)

        cls.raditz = raditz = OrgUnit.objects.create(
            uuid="702dbae8-0f47-4065-ad0c-b2557f31cc96",
            org_unit_type=super_saiyans,
            version=sw_version,
            name="Raditz",
            validation_status=OrgUnit.VALIDATION_VALID,
        )

        cls.bardock = bardock = OrgUnit.objects.create(
            parent=None,
            org_unit_type=warriors,
            version=sw_version,
            name="Bardock",
            validation_status=OrgUnit.VALIDATION_VALID,
            simplified_geom=MultiPolygon(Polygon([(1, 2), (3, 4), (5, 6), (1, 2)])),
        )

        raditz.parent = bardock
        raditz.save()

        # bardock
        #  -goku
        #    - gohan
        #    - goten

        cls.goku = goku = OrgUnit.objects.create(
            parent=bardock,
            org_unit_type=super_saiyans,
            version=sw_version,
            name="Son Goku",
            validation_status=OrgUnit.VALIDATION_REJECTED,
        )

        cls.gohan = OrgUnit.objects.create(
            parent=goku,
            org_unit_type=on_earth,
            version=sw_version,
            name="Son Gohan",
            validation_status=OrgUnit.VALIDATION_VALID,
        )

        cls.goten = OrgUnit.objects.create(
            parent=goku,
            org_unit_type=on_earth,
            version=sw_version,
            name="Son Goten",
            validation_status=OrgUnit.VALIDATION_VALID,
            location=Point(-4, -5, 0),
        )

        group_2.org_units.set([bardock, goku])
        user.iaso_profile.org_units.set([raditz, goku])

    def test_orgunits_list_without_auth_for_project_requiring_auth(self):
        """GET /mobile/orgunits/ without auth for project which requires it: 401"""

        response = self.client.get(BASE_URL, {APP_ID: self.project.app_id})
        self.assertJSONResponse(response, 401)

    def test_orgunits_list_with_wrong_auth_for_project_requiring_auth(self):
        """GET /mobile/orgunits/ with wrong auth for project which requires it: 401"""

        self.client.force_authenticate(user=self.user2)
        response = self.client.get(BASE_URL, {APP_ID: self.project.app_id})
        self.assertJSONResponse(response, 401)

    def test_orgunits_list_with_auth_for_project_requiring_auth(self):
        """GET /mobile/orgunits/ with auth for project which requires it: 200"""

        self.client.force_authenticate(user=self.user)
        response = self.client.get(BASE_URL, {APP_ID: self.project.app_id})
        self.assertJSONResponse(response, 200)

    def test_org_unit_have_correct_parent_id_without_limit(self):
        self.client.force_authenticate(self.user)

        response = self.client.get(BASE_URL, data={APP_ID: BASE_APP_ID})
        self.assertJSONResponse(response, 200)
        self.assertEqual([self.raditz.id, self.goku.id], response.json()["roots"])
        self.assertNotIn("count", response.json())
        self.assertNotIn("next", response.json())
        self.assertNotIn("previous", response.json())
        self.assertEqual(len(response.json()["orgUnits"]), 4)
        self.assertEqual(response.json()["orgUnits"][0]["name"], "Bardock")
        self.assertEqual(response.json()["orgUnits"][0]["parent_id"], None)
        self.assertEqual(1, len(response.json()["orgUnits"][0]["groups"]))
        self.assertEqual(response.json()["orgUnits"][0]["groups"][0], self.group_2.id)
        self.assertEqual(response.json()["orgUnits"][1]["name"], "Raditz")
        self.assertEqual(response.json()["orgUnits"][1]["parent_id"], self.bardock.id)
        self.assertEqual(0, len(response.json()["orgUnits"][1]["groups"]))
        self.assertEqual(response.json()["orgUnits"][2]["name"], "Son Gohan")
        self.assertEqual(response.json()["orgUnits"][2]["parent_id"], None)
        self.assertEqual(0, len(response.json()["orgUnits"][2]["groups"]))
        self.assertEqual(response.json()["orgUnits"][3]["name"], "Son Goten")
        self.assertEqual(response.json()["orgUnits"][3]["parent_id"], None)
        self.assertEqual(0, len(response.json()["orgUnits"][3]["groups"]))

    def test_org_unit_have_correct_parent_id_with_limit(self):
        self.client.force_authenticate(self.user)

        response = self.client.get(BASE_URL, data={APP_ID: BASE_APP_ID, LIMIT: 1, PAGE: 1})
        self.assertJSONResponse(response, 200)
        self.assert_page(response.json(), count=4, limit=1, page=1, pages=4, has_next=True, has_previous=False)
        self.assertEqual([self.raditz.id, self.goku.id], response.json()["roots"])
        self.assertEqual(len(response.json()["orgUnits"]), 1)
        self.assertEqual(response.json()["orgUnits"][0]["name"], "Bardock")
        self.assertEqual(response.json()["orgUnits"][0]["parent_id"], None)

        response = self.client.get(BASE_URL, data={APP_ID: BASE_APP_ID, LIMIT: 1, PAGE: 2})
        self.assertJSONResponse(response, 200)
        self.assert_page(response.json(), count=4, limit=1, page=2, pages=4, has_next=True, has_previous=True)
        self.assertNotIn("roots", response.json())
        self.assertEqual(len(response.json()["orgUnits"]), 1)
        self.assertEqual(response.json()["orgUnits"][0]["name"], "Raditz")
        self.assertEqual(response.json()["orgUnits"][0]["parent_id"], self.bardock.id)

        response = self.client.get(BASE_URL, data={APP_ID: BASE_APP_ID, LIMIT: 2, PAGE: 2})
        self.assertJSONResponse(response, 200)
        self.assert_page(response.json(), count=4, limit=2, page=2, pages=2, has_next=False, has_previous=True)
        self.assertNotIn("roots", response.json())
        self.assertEqual(len(response.json()["orgUnits"]), 2)
        self.assertEqual(response.json()["orgUnits"][0]["name"], "Son Gohan")
        self.assertEqual(response.json()["orgUnits"][0]["parent_id"], None)
        self.assertEqual(response.json()["orgUnits"][1]["name"], "Son Goten")
        self.assertEqual(response.json()["orgUnits"][1]["parent_id"], None)
        self.assertNotIn("geojson", response.json()["orgUnits"][1])

    def assert_page(self, json, count: int, limit: int, page: int, pages: int, has_next: bool, has_previous: bool):
        self.assertEqual(json["count"], count)
        self.assertEqual(json["limit"], limit)
        self.assertEqual(json["page"], page)
        self.assertEqual(json["pages"], pages)
        self.assertEqual(json["has_next"], has_next)
        self.assertEqual(json["has_previous"], has_previous)

    def test_org_unit_have_correct_parent_id_without_limit_with_shape(self):
        self.client.force_authenticate(self.user)

        response = self.client.get(BASE_URL, data={APP_ID: BASE_APP_ID, "shapes": "true"}, format="json")
        self.assertJSONResponse(response, 200)
        self.assertEqual([self.raditz.id, self.goku.id], response.json()["roots"])
        self.assertNotIn("count", response.json())
        self.assertNotIn("next", response.json())
        self.assertNotIn("previous", response.json())
        self.assertEqual(len(response.json()["orgUnits"]), 4)
        self.assertEqual(response.json()["orgUnits"][0]["name"], "Bardock")
        self.assertEqual(response.json()["orgUnits"][0]["parent_id"], None)
        self.assertEqual(
            response.json()["orgUnits"][0]["geo_json"],
            {"type": "MultiPolygon", "coordinates": [[[[1, 2], [3, 4], [5, 6], [1, 2]]]]},
        )
        self.assertEqual(response.json()["orgUnits"][1]["name"], "Raditz")
        self.assertEqual(response.json()["orgUnits"][1]["parent_id"], self.bardock.id)
        self.assertEqual(response.json()["orgUnits"][1]["geo_json"], None)

    def test_LIMIT_OU_DOWNLOAD_TO_ROOTS(self):
        self.user.iaso_profile.org_units.set([self.goku])
        self.goku.validation_status = OrgUnit.VALIDATION_VALID
        self.goku.save()
        self.client.force_authenticate(self.user)
        response = self.client.get(BASE_URL, data={APP_ID: BASE_APP_ID})
        j = self.assertJSONResponse(response, 200)
        # set limit on user

        self.assertEqual([self.goku.id], j["roots"])
        self.assertNotIn("count", j)
        self.assertNotIn("next", j)
        self.assertNotIn("previous", j)
        self.assertEqual(len(j["orgUnits"]), 5)

        ff, _created = FeatureFlag.objects.get_or_create(
            code=FeatureFlag.LIMIT_OU_DOWNLOAD_TO_ROOTS
        )  # created via migrations
        self.project.feature_flags.add(ff)
        cache.clear()  # to fix cache don't clear when the feature flags are modified
        self.client.force_authenticate(self.user)
        response = self.client.get(BASE_URL, data={APP_ID: BASE_APP_ID})
        j = self.assertJSONResponse(response, 200)
        self.assertEqual([self.goku.id], j["roots"])
        self.assertNotIn("count", j)
        self.assertNotIn("next", j)
        self.assertNotIn("previous", j)
        self.assertEqual(len(j["orgUnits"]), 3)

    def test_boundingbox(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(BOUNDINGXBOX_URL, data={APP_ID: BASE_APP_ID})
        j = self.assertJSONResponse(response, 200)

        bbox = j["results"][0]
        self.assertEqual(bbox, {"east": -5.024, "northern": 1.0, "south": -3.976, "west": 6.0})

    def test_boundingbox_with_user_limit(self):
        ff, _created = FeatureFlag.objects.get_or_create(
            code=FeatureFlag.LIMIT_OU_DOWNLOAD_TO_ROOTS
        )  # created via migrations
        self.project.feature_flags.add(ff)
        cache.clear()  # to fix cache don't clear when the feature flags are modified
        self.user.iaso_profile.org_units.set([self.goten])
        self.client.force_authenticate(self.user)
        response = self.client.get(BOUNDINGXBOX_URL, data={APP_ID: BASE_APP_ID})
        j = self.assertJSONResponse(response, 200)
        # set limit on user
        bbox = j["results"][0]
        self.assertEqual(bbox, {"east": -5.024, "northern": -4.024, "south": -3.976, "west": -4.976})

    @time_machine.travel("2023-10-26T09:00:00.000Z", tick=False)
    def test_reference_instances(self):
        # Instance 1.
        form1 = Form.objects.create(name="Form 1")
        form_version1 = FormVersion.objects.create(form=form1, version_id=1)
        instance1 = Instance.objects.create(
            form=form1, org_unit=self.raditz, json={"key": "foo"}, form_version=form_version1
        )
        # Instance 2.
        form2 = Form.objects.create(name="Form 2")
        form_version2 = FormVersion.objects.create(form=form2, version_id=5)
        instance2 = Instance.objects.create(
            form=form2, org_unit=self.raditz, json={"key": "bar"}, form_version=form_version2
        )
        # Mark instances as reference instances.
        OrgUnitReferenceInstance.objects.create(org_unit=self.raditz, instance=instance1, form=form1)
        OrgUnitReferenceInstance.objects.create(org_unit=self.raditz, instance=instance2, form=form2)

        self.client.force_authenticate(self.user)

        params = {APP_ID: BASE_APP_ID}

        # Fetch OrgUnit by ID.
        response1 = self.client.get(f"{BASE_URL}{self.raditz.pk}/reference_instances/", data=params)
        self.assertJSONResponse(response1, 200)

        # Fetch OrgUnit by UUID.
        response2 = self.client.get(f"{BASE_URL}{self.raditz.uuid}/reference_instances/", data=params)
        self.assertJSONResponse(response2, 200)

        self.assertEqual(response1.data, response2.data)
        self.assertEqual(
            response1.data,
            {
                "count": 2,
                "instances": [
                    {
                        "id": instance1.pk,
                        "uuid": None,
                        "form_id": form1.id,
                        "form_version_id": form_version1.id,
                        "created_at": 1698310800.0,
                        "updated_at": 1698310800.0,
                        "json": {"key": "foo"},
                    },
                    {
                        "id": instance2.pk,
                        "uuid": None,
                        "form_id": form2.id,
                        "form_version_id": form_version2.id,
                        "created_at": 1698310800.0,
                        "updated_at": 1698310800.0,
                        "json": {"key": "bar"},
                    },
                ],
                "has_next": False,
                "has_previous": False,
                "page": 1,
                "pages": 1,
                "limit": 10,
            },
        )

        # Ensure soft deleted instances are not returned.

        instance2.deleted = True
        instance2.save()

        response = self.client.get(f"{BASE_URL}{self.raditz.pk}/reference_instances/", data=params)
        self.assertJSONResponse(response, 200)
        self.assertEqual(
            response.data,
            {
                "count": 1,
                "instances": [
                    {
                        "id": instance1.pk,
                        "uuid": None,
                        "form_id": form1.id,
                        "form_version_id": form_version1.id,
                        "created_at": 1698310800.0,
                        "updated_at": 1698310800.0,
                        "json": {"key": "foo"},
                    },
                ],
                "has_next": False,
                "has_previous": False,
                "page": 1,
                "pages": 1,
                "limit": 10,
            },
        )

    def test_post_to_retrieve_list(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(
            BASE_URL, data={APP_ID: BASE_APP_ID, IDS: f"{self.goku.id},{self.gohan.id},{self.goten.id}"}
        )
        org_units = self.assertJSONResponse(response, 200)
        self.assertEqual(len(org_units["orgUnits"]), 3)
        self.assertEqual(org_units["orgUnits"][0]["id"], self.goku.id)
        self.assertEqual(org_units["orgUnits"][0]["validation_status"], OrgUnit.VALIDATION_REJECTED)
        self.assertEqual(org_units["orgUnits"][1]["id"], self.gohan.id)
        self.assertEqual(org_units["orgUnits"][1]["validation_status"], OrgUnit.VALIDATION_VALID)
        self.assertEqual(org_units["orgUnits"][2]["id"], self.goten.id)
        self.assertEqual(org_units["orgUnits"][2]["validation_status"], OrgUnit.VALIDATION_VALID)

    def test_post_to_retrieve_list_with_wrong_id(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(BASE_URL, data={APP_ID: BASE_APP_ID, IDS: f"{self.goku.id},-1,{self.goten.id}"})
        self.assertEqual(response.status_code, 404)
