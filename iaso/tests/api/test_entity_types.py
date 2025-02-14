import json
from unittest import mock

from django.core.files import File

from iaso import models as m
from iaso.models import Entity, EntityType, FormVersion, Instance, Project
from iaso.test import APITestCase


class EntityTypeAPITestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.star_wars = m.Account.objects.create(name="Star Wars")
        cls.the_gang = m.Account.objects.create(name="The Gang")

        sw_source = m.DataSource.objects.create(name="Galactic Empire")
        cls.sw_source = sw_source
        sw_version = m.SourceVersion.objects.create(data_source=sw_source, number=1)
        cls.star_wars.default_version = sw_version
        cls.star_wars.save()
        cls.sw_version = sw_version

        cls.yoda = cls.create_user_with_profile(
            username="yoda", account=cls.star_wars, permissions=["iaso_submissions", "iaso_entity_type_write"]
        )
        cls.chewie = cls.create_user_with_profile(
            username="chewie", account=cls.star_wars, permissions=["iaso_submissions"]
        )

        cls.jedi_council = m.OrgUnitType.objects.create(name="Jedi Council", short_name="Cnc")

        cls.jedi_council_corruscant = m.OrgUnit.objects.create(
            name="Coruscant Jedi Council", validation_status=m.OrgUnit.VALIDATION_VALID
        )
        cls.jedi_council_corruscan_unvalidated = m.OrgUnit.objects.create(name="Coruscant Jedi Council")

        cls.project = m.Project.objects.create(
            name="Hydroponic gardens", app_id="stars.empire.agriculture.hydroponics", account=cls.star_wars
        )

        cls.form_1 = m.Form.objects.create(name="Hydroponics study", period_type=m.MONTH, single_per_period=True)

        cls.create_form_instance(
            form=cls.form_1, period="202001", org_unit=cls.jedi_council_corruscant, project=cls.project
        )
        cls.create_form_instance(
            form=cls.form_1, period="202002", org_unit=cls.jedi_council_corruscant, project=cls.project
        )
        cls.create_form_instance(
            form=cls.form_1, period="202002", org_unit=cls.jedi_council_corruscant, project=cls.project
        )
        cls.create_form_instance(
            form=cls.form_1, period="202003", org_unit=cls.jedi_council_corruscant, project=cls.project
        )

        cls.instance_with_unvalidated_ou = cls.create_form_instance(
            form=cls.form_1, period="202004", org_unit=cls.jedi_council_corruscan_unvalidated, project=cls.project
        )

        cls.form_2 = m.Form.objects.create(
            name="Hydroponic public survey",
            form_id="sample2",
            device_field="deviceid",
            location_field="geoloc",
            period_type="QUARTER",
            single_per_period=True,
        )

        # Form without period
        cls.form_3 = m.Form.objects.create(
            name="Hydroponic public survey III",
            form_id="sample34",
            device_field="deviceid",
            location_field="geoloc",
            # period_type="QUARTER",
            # single_per_period=True,
        )

        cls.form_4 = m.Form.objects.create(
            name="Hydroponic public survey IV",
            form_id="sample26",
            device_field="deviceid",
            location_field="geoloc",
            period_type="QUARTER",
            single_per_period=True,
        )

        form_2_file_mock = mock.MagicMock(spec=File)
        form_2_file_mock.name = "test.xml"
        cls.form_2.form_versions.create(file=form_2_file_mock, version_id="2020022401")
        cls.form_2.org_unit_types.add(cls.jedi_council)
        cls.create_form_instance(form=cls.form_2, period="202001", org_unit=cls.jedi_council_corruscant, project=None)
        cls.form_2.save()

        # Instance saved without period
        cls.form_3.form_versions.create(file=form_2_file_mock, version_id="2020022401")
        cls.form_3.org_unit_types.add(cls.jedi_council)
        cls.create_form_instance(form=cls.form_3, org_unit=cls.jedi_council_corruscant, project=None)
        cls.form_3.save()

        # A deleted Instance
        cls.form_4.form_versions.create(file=form_2_file_mock, version_id="2020022402")
        cls.form_4.org_unit_types.add(cls.jedi_council)
        cls.create_form_instance(
            form=cls.form_4, period="2020Q1", org_unit=cls.jedi_council_corruscant, deleted=True, project=None
        )
        cls.form_4.save()

        cls.project.unit_types.add(cls.jedi_council)
        cls.project.forms.add(cls.form_1)
        cls.project.forms.add(cls.form_2)
        cls.project.forms.add(cls.form_3)
        cls.project.forms.add(cls.form_4)
        sw_source.projects.add(cls.project)
        cls.project.save()

    def test_create_entity_type(self):
        self.client.force_authenticate(self.yoda)

        payload = {
            "name": "New Entity Type",
            "reference_form": self.form_1.id,
            "account": self.yoda.iaso_profile.account.pk,
        }

        response = self.client.post("/api/entitytypes/", data=payload, format="json")

        self.assertEqual(response.status_code, 201)

    def test_create_entity_type_without_permission(self):
        self.client.force_authenticate(self.chewie)

        payload = {
            "name": "New Entity Type",
            "reference_form": self.form_1.id,
            "account": self.yoda.iaso_profile.account.pk,
        }

        response = self.client.post("/api/entitytypes/", data=payload, format="json")

        self.assertEqual(response.status_code, 403)

    def test_get_entity_type(self):
        self.client.force_authenticate(self.yoda)

        payload = {
            "name": "New Entity Type",
            "reference_form": self.form_1.id,
        }

        self.client.post("/api/entitytypes/", data=payload, format="json")

        response = self.client.get("/api/entitytypes/", format="json")

        self.assertEqual(response.status_code, 200)

    def test_update_entity_type(self):
        self.client.force_authenticate(self.yoda)

        post_payload = {
            "name": "New Entity Type_test",
            "reference_form": self.form_1.id,
            "account": self.yoda.iaso_profile.account.pk,
        }

        self.client.post("/api/entitytypes/", data=post_payload, format="json")

        patch_payload = {
            "name": "New Entity Type_test_2",
            "reference_form": self.form_1.id,
            "account": self.yoda.iaso_profile.account.pk,
        }

        response = self.client.patch(
            "/api/entitytypes/{0}/".format(EntityType.objects.last().pk), data=patch_payload, format="json"
        )
        self.assertEqual(response.status_code, 200)

    def test_update_entity_type_without_permission(self):
        self.client.force_authenticate(self.yoda)

        post_payload = {
            "name": "New Entity Type_test",
            "reference_form": self.form_1.id,
            "account": self.yoda.iaso_profile.account.pk,
        }
        self.client.post("/api/entitytypes/", data=post_payload, format="json")

        self.client.force_authenticate(self.chewie)

        patch_payload = {
            "name": "New Entity Type_test_2",
            "reference_form": self.form_1.id,
            "account": self.yoda.iaso_profile.account.pk,
        }

        response = self.client.patch(
            "/api/entitytypes/{0}/".format(EntityType.objects.last().pk), data=patch_payload, format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_entity_type_are_unique_per_account(self):
        self.client.force_authenticate(self.yoda)

        EntityType.objects.create(
            name="beneficiary", reference_form=self.form_1, account=self.yoda.iaso_profile.account
        )

        payload = {
            "name": "beneficiary",
            "reference_form": self.form_1.id,
            "account": self.yoda.iaso_profile.account.pk,
        }

        response = self.client.post("/api/entitytypes/", data=payload, format="json")

        self.assertEqual(response.status_code, 400)

    def test_entity_types_are_multitenancy(self):
        self.client.force_authenticate(self.yoda)
        EntityType.objects.create(
            name="beneficiary", reference_form=self.form_1, account=self.yoda.iaso_profile.account
        )

        payload = {"name": "beneficiary", "reference_form": self.form_1.id, "account": self.the_gang.pk}

        response = self.client.post("/api/entitytypes/", data=payload, format="json")
        get_response = self.client.get("/api/entitytypes/")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(get_response.json()), 1)

    def test_get_mobile_entity_types(self):
        self.client.force_authenticate(self.yoda)
        account = self.yoda.iaso_profile.account
        name = "beneficiary"
        code = f"{name}_{account.id}"
        # same account as logged user
        EntityType.objects.create(name=name, reference_form=self.form_1, account=account, code=code)

        # different account
        EntityType.objects.create(
            name=name,
            reference_form=self.form_1,
            account=self.the_gang,
            code=f"{name}_{self.the_gang.id}",
        )

        response = self.client.get(f"/api/mobile/entitytypes/?app_id={self.project.app_id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["code"], code)

    def test_get_entities_by_entity_type(self):
        self.client.force_authenticate(self.yoda)

        file = File(open("iaso/tests/fixtures/test_entity_data.xml", "rb"))
        instance = Instance.objects.get(period=202001, form=self.form_1)
        instance.file = file
        instance.uuid = "2b05d9ab-2ak9-4080-ab4d-03661fb29730"
        instance.json = {
            "muac": "13",
            "oedema": "0",
            "y_prog": "prog_otp",
            "_version": "2022090601",
            "ref_to_sc": "The child will be referred to SC!",
            "instanceID": "uuid:4901dff4-30af-49e2-afd1-42970bb8f03d",
            "child_color": "muac_green",
            "confirm_otp": "",
            "g_admi_type": "mam",
            "color_answer": "Green ðŸŸ¢",
            "color_output": "",
            "counsuelling_type": "therap_foods",
        }
        instance.save()

        instance2 = self.instance_with_unvalidated_ou
        instance2.file = file
        instance2.uuid = "2b05d9ab-2ak9-4080-ab4d-03661fb29739"
        instance2.json = {
            "muac": "13",
            "oedema": "0",
            "y_prog": "prog_otp",
            "_version": "2022090601",
            "ref_to_sc": "The child will be referred to SC!",
            "instanceID": "uuid:4901dff4-30af-49e2-afd1-42970bb8f03d",
            "child_color": "muac_green",
            "confirm_otp": "",
            "g_admi_type": "mam",
            "color_answer": "Green ðŸŸ¢",
            "color_output": "",
            "counsuelling_type": "therap_foods",
        }
        instance2.save()

        instance3 = Instance.objects.create(
            period=202001, form=self.form_1, org_unit=self.jedi_council_corruscant, project=self.project
        )
        instance3.file = file
        instance3.uuid = "2b05d9ab-2ak9-4080-ab4d-03661fb29733"
        instance3.json = {
            "muac": "13",
            "oedema": "0",
            "y_prog": "prog_otp",
            "_version": "2022090601",
            "ref_to_sc": "The child will be referred to SC!",
            "instanceID": "uuid:4901dff4-30af-49e2-afd1-42970bb8f03d",
            "child_color": "muac_green",
            "confirm_otp": "",
            "g_admi_type": "mam",
            "color_answer": "Green ðŸŸ¢",
            "color_output": "",
            "counsuelling_type": "therap_foods",
        }
        instance3.save()

        FormVersion.objects.create(version_id="2022090601", form_id=instance.form.id)

        entity_type, created = EntityType.objects.get_or_create(
            name="beneficiary", reference_form=self.form_1, account=self.yoda.iaso_profile.account
        )

        second_entity_type, created = EntityType.objects.get_or_create(
            name="children under 5", reference_form=self.form_1, account=self.yoda.iaso_profile.account
        )

        entity_with_data = Entity.objects.create(
            name="New Client",
            account=self.yoda.iaso_profile.account,
            entity_type=entity_type,
            attributes=instance,
        )

        entity_with_data2 = Entity.objects.create(
            name="New Client",
            account=self.yoda.iaso_profile.account,
            entity_type=entity_type,
            attributes=instance2,
        )

        entity_with_data3 = Entity.objects.create(
            name="New Client",
            account=self.yoda.iaso_profile.account,
            entity_type=second_entity_type,
            attributes=instance3,
        )

        instance.entity = entity_with_data
        instance.save()

        # Shouldn't appear in the list as the refered OU is not validated.
        instance2.entity = entity_with_data2
        instance2.save()

        instance3.entity = entity_with_data3
        instance3.save()

        entity_type.refresh_from_db()
        second_entity_type.refresh_from_db()

        response = self.client.get(f"/api/mobile/entitytypes/{entity_type.pk}/entities/?app_id={self.project.app_id}")

        self.assertEqual(response.json()["count"], 2)

        response_entity_instance = response.json()["results"][0]["instances"]

        self.assertEqual(response_entity_instance[0]["json"]["muac"], "13")
        self.assertEqual(response_entity_instance[0]["json"], instance.json)

        response = self.client.get(
            f"/api/mobile/entitytypes/{second_entity_type.pk}/entities/?app_id={self.project.app_id}"
        )

        self.assertEqual(response.json()["count"], 1)

    def test_get_entities_by_entity_type_respect_app_id(self):
        self.client.force_authenticate(self.yoda)

        entity_type, created = EntityType.objects.get_or_create(
            name="beneficiary", reference_form=self.form_1, account=self.yoda.iaso_profile.account
        )

        app_id = "APP_ID"

        project = Project.objects.create(name="Project 1", app_id=app_id, account=self.star_wars)

        instance_app_id = Instance.objects.create(
            org_unit=self.jedi_council_corruscant,
            form=self.form_1,
            period="202002",
            project=project,
            uuid="9335359a-9f80-422d-997a-68ae7e39d9g3",
        )
        instance_app_id.file = File(open("iaso/tests/fixtures/test_entity_data2.xml", "rb"))
        instance_app_id.json = {
            "name": "Prince of Euphor",
            "father_name": "Professor Procyon",
            "age_type": 0,
            "birth_date": "1978-07-03",
            "gender": "male",
            "hc": "hc_C",
            "_version": "2022090602",
            "instanceID": "uuid:4901dff4-30af-49e2-afd1-42970bb8f03e",
        }
        instance_app_id.save()

        FormVersion.objects.create(version_id="2022090602", form_id=instance_app_id.form.id)

        self.form_1.instances.add(instance_app_id)
        self.form_1.save()

        entity_with_data = Entity.objects.create(
            name="New Client",
            account=self.yoda.iaso_profile.account,
            entity_type=entity_type,
            attributes=instance_app_id,
        )

        instance_app_id.entity = entity_with_data
        instance_app_id.save()

        response = self.client.get(f"/api/mobile/entitytypes/{entity_type.pk}/entities/?app_id={app_id}")

        response_json = response.json()

        self.assertEqual(response_json["count"], 1)
        self.assertEqual(response_json["results"][0]["entity_type_id"], str(entity_type.id))

        response_entity_instance = response_json["results"][0]["instances"]

        self.assertEqual(response_entity_instance[0]["id"], instance_app_id.uuid)
        self.assertEqual(response_entity_instance[0]["json"], instance_app_id.json)

    def test_get_entities_by_entity_type_filtered_by_json_content(self):
        self.client.force_authenticate(self.yoda)

        FormVersion.objects.create(version_id="2022090601", form=self.form_1)
        entity_type = EntityType.objects.create(
            name="Heroes", reference_form=self.form_1, account=self.yoda.iaso_profile.account
        )

        instance = Instance.objects.create(period=202001, form=self.form_1, project=self.project)
        instance.org_unit = self.jedi_council_corruscant
        instance.file = File(open("iaso/tests/fixtures/test_entity_data.xml", "rb"))
        instance.uuid = "2b05d9ab-2ak9-4080-ab4d-03661fb29730"
        instance.json = {
            "name": "Don Diego de la Vega",
            "father_name": "Don Alejandro de la Vega",
            "age_type": 0,
            "birth_date": "1919-08-09",
            "gender": "male",
            "hc": "hc_C",
            "_version": "2022090601",
            "instanceID": "uuid:4901dff4-30af-49e2-afd1-42970bb8f03d",
        }
        instance.save()
        instance.entity = Entity.objects.create(
            name="Zorro",
            account=self.yoda.iaso_profile.account,
            entity_type=entity_type,
            attributes=instance,
        )
        instance.save()

        # this one shouldn't appear as it is linked to a unvalidated org unit.
        instance2 = Instance.objects.create(period=202001, form=self.form_1, project=self.project)
        instance2.org_unit = self.jedi_council_corruscant
        instance2.file = File(open("iaso/tests/fixtures/test_entity_data2.xml", "rb"))
        instance2.uuid = "2b05d9ab-2ak9-4080-ab4d-03661fb29731"
        instance2.json = {
            "name": "robert of Euphor",
            "father_name": "Professor Procyon",
            "age_type": 0,
            "birth_date": "1978-07-03",
            "gender": "male",
            "hc": "hc_C",
            "_version": "2022090601",
            "instanceID": "uuid:4901dff4-30af-49e2-afd1-42970bb8f03e",
        }
        instance2.save()
        instance2.entity = Entity.objects.create(
            name="Actarus",
            account=self.yoda.iaso_profile.account,
            entity_type=entity_type,
            attributes=instance2,
        )
        instance2.save()

        entity_type.refresh_from_db()

        json_content = json.dumps({"in": ["robert", {"var": "name"}]})
        response = self.client.get(
            f"/api/mobile/entitytypes/{entity_type.pk}/entities/",
            {"json_content": json_content, "app_id": self.project.app_id},
            format="json",
        )
        self.assertEqual(response.json()["count"], 1)

        response_entity_instance = response.json()["results"][0]["instances"]

        self.assertEqual(response_entity_instance[0]["id"], instance2.uuid)
        self.assertEqual(response_entity_instance[0]["json"], instance2.json)

    def test_entity_types_are_account_restricted(self):
        self.client.force_authenticate(self.yoda)

        EntityType.objects.create(name="restricted", reference_form=self.form_1, account=self.the_gang)
        EntityType.objects.create(name="allowed", reference_form=self.form_1, account=self.yoda.iaso_profile.account)

        response = self.client.get(f"/api/mobile/entitytypes/?app_id={self.project.app_id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["name"], "allowed")
