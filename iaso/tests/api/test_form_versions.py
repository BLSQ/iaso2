import tempfile
import typing
from unittest import mock

from django.core.files import File
from django.core.files.uploadedfile import UploadedFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from iaso import models as m
from iaso.api.query_params import APP_ID
from iaso.test import APITestCase


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class FormsVersionAPITestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        star_wars = m.Account.objects.create(name="Star Wars")
        dc = m.Account.objects.create(name="DC Comics")

        sw_source = m.DataSource.objects.create(name="Evil Empire")
        cls.sw_source = sw_source
        sw_version = m.SourceVersion.objects.create(data_source=sw_source, number=1)
        star_wars.default_version = sw_version
        star_wars.save()

        cls.yoda = cls.create_user_with_profile(username="yoda", account=star_wars, permissions=["iaso_forms"])
        cls.batman = cls.create_user_with_profile(username="batman", account=dc, permissions=["iaso_forms"])
        cls.superman = cls.create_user_with_profile(username="superman", account=dc)

        cls.sith_council = m.OrgUnitType.objects.create(name="Sith Council", short_name="Cnc")

        cls.project = m.Project.objects.create(
            name="Hydroponic gardens",
            app_id="stars.empire.agriculture.hydroponics",
            account=star_wars,
            needs_authentication=True,
        )
        cls.project.unit_types.add(cls.sith_council)

        cls.form_1 = m.Form.objects.create(
            name="New Land Speeder concept",  # no form_id yet (no version)
            period_type="QUARTER",
            single_per_period=True,
        )
        cls.form_1.org_unit_types.add(cls.sith_council)
        cls.form_1.save()
        cls.project.forms.add(cls.form_1)
        cls.project.save()

        cls.form_2 = m.Form.objects.create(
            name="Death Start survey", form_id="sample2", period_type="MONTH", single_per_period=False
        )
        cls.form_2.org_unit_types.add(cls.sith_council)
        cls.form_1.save()
        form_2_file_mock = mock.MagicMock(spec=File)
        form_2_file_mock.name = "test.xml"
        with open("iaso/tests/fixtures/odk_form_valid_no_settings.xlsx", "rb") as xls_file:
            cls.form_2.form_versions.create(
                file=form_2_file_mock, xls_file=UploadedFile(xls_file), version_id="2020022401"
            )
        cls.project.forms.add(cls.form_2)

        cls.project.save()

    def test_form_version_to_questions_by_path(self):
        self.client.force_authenticate(self.yoda)
        with open("iaso/tests/fixtures/odk_valid_multi_select.xlsx", "rb") as xls_file:
            response = self.client.post(
                f"/api/formversions/",
                data={"form_id": self.form_1.id, "xls_file": xls_file},
                format="multipart",
                headers={"accept": "application/json"},
            )

        questions_by_path = self.form_1.form_versions.first().questions_by_path()
        questions_by_name = self.form_1.form_versions.first().questions_by_name()
        self.assertEqual(
            [x for x in questions_by_name.keys()],
            [
                "demo_integer",
                "demo_text",
                "source_elec",
                "demo_note",
                "demo_select_one",
                "demo_calculate",
                "other_source_elec",
                "instanceID",
            ],
        )

        self.assertEqual(
            [x for x in questions_by_path.keys()],
            [
                "signalitic/demo_integer",
                "signalitic/demo_text",
                "source_elec",
                "demo_note",
                "demo_select_one",
                "demo_calculate",
                "propriete_fonciere/other_source_elec",
                "meta/instanceID",
            ],
        )

    def test_form_submission_xml_to_json(self):
        self.jedi_council_coruscant = m.OrgUnit.objects.create(
            name="Coruscant Jedi Council", org_unit_type=self.sith_council
        )
        self.client.force_authenticate(self.yoda)
        with open("iaso/tests/fixtures/odk_valid_multi_select.xlsx", "rb") as xls_file:
            response = self.client.post(
                f"/api/formversions/",
                data={"form_id": self.form_1.id, "xls_file": xls_file},
                format="multipart",
                headers={"accept": "application/json"},
            )

        version_id = response.json()["version_id"]

        file_content = " ".join(
            [
                '<?xml version=\'1.0\' ?><data id="carte_sanitaire" version="'
                + version_id
                + '" xmlns:ev="http://www.w3.org/2001/xml-events" xmlns:orx="http://openrosa.org/xforms" xmlns:odk="http://www.opendatakit.org/xforms" xmlns:h="http://www.w3.org/1999/xhtml" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:jr="http://openrosa.org/javarosa">',
                "<meta><instanceID>uuid:3c185364-e5dc-4912-98b2-e9aeb23049f5</instanceID></meta>",
                "<source_elec>B</source_elec>"
                "<propriete_fonciere><other_source_elec>AA</other_source_elec></propriete_fonciere>",
                "</data>",
            ]
        )
        instance = m.Instance.objects.create(
            form=self.form_1,
            period="202001",
            org_unit=self.jedi_council_coruscant,
            file=SimpleUploadedFile("test_file.xml", file_content.encode("utf-8")),
        )

        json_instance = instance.get_and_save_json_of_xml()
        self.assertEqual(
            {
                "_version": version_id,
                "instanceID": "uuid:3c185364-e5dc-4912-98b2-e9aeb23049f5",
                "other_source_elec": "AA",
                "source_elec": "B",
            },
            json_instance,
        )

    def test_form_versions_list(self):
        """GET /formversions/: allowed"""

        self.client.force_authenticate(self.yoda)
        response = self.client.get("/api/formversions/")
        self.assertJSONResponse(response, 200)
        form_versions_data = response.json()["form_versions"]

        for form_version_data in form_versions_data:
            self.assertValidFormVersionData(form_version_data)
            self.assertNotIn("descriptor", form_version_data)

    def test_form_versions_retrieve(self):
        """GET /formversions/<form_id>: allowed"""

        self.client.force_authenticate(self.yoda)
        response = self.client.get(f"/api/formversions/{self.form_2.form_versions.first().id}/?fields=:all")
        self.assertJSONResponse(response, 200)
        form_version_data = response.json()
        self.assertValidFormVersionData(form_version_data)
        self.assertHasField(form_version_data, "descriptor", dict)

    def test_form_versions_update(self):
        """PUT /formversions/<form_id>: ok"""
        self.client.force_authenticate(self.yoda)

        start_period = "BIG BANG"
        end_period = "DOOMSDAY"
        response = self.client.put(
            f"/api/formversions/{self.form_2 .form_versions.first().id}/",
            data={
                "end_period": end_period,
                "form_id": self.form_2.id,
                "start_period": start_period,
            },
            format="json",
        )
        response_data = response.json()
        self.assertJSONResponse(response, 200)
        self.assertEqual(response_data["start_period"], start_period)
        self.assertEqual(response_data["end_period"], end_period)

    def test_form_versions_patch(self):
        """PUT /formversions/<form_id>: ok"""
        self.client.force_authenticate(self.yoda)

        start_period = "BIG BANG"
        end_period = "DOOMSDAY"
        response = self.client.patch(
            f"/api/formversions/{self.form_2 .form_versions.first().id}/",
            data={
                "end_period": end_period,
                "form_id": self.form_2.id,
                "start_period": start_period,
            },
            format="json",
        )
        response_data = response.json()
        self.assertJSONResponse(response, 200)
        self.assertEqual(response_data["start_period"], start_period)
        self.assertEqual(response_data["end_period"], end_period)

    def test_form_versions_destroy(self):
        """DELETE /formversions/<form_id>: not authorized for now"""

        self.client.force_authenticate(self.yoda)
        response = self.client.delete(f"/api/formversions/33/")
        self.assertJSONResponse(response, 405)

    def test_form_versions_create_ok_first_version(self):
        """POST /form-versions/ happy path (first version)"""

        self.client.force_authenticate(self.yoda)
        with open("iaso/tests/fixtures/odk_form_valid_sample1_2020022401.xlsx", "rb") as xls_file:
            response = self.client.post(
                f"/api/formversions/",
                data={"form_id": self.form_1.id, "xls_file": xls_file},
                format="multipart",
                headers={"accept": "application/json"},
            )
        self.assertJSONResponse(response, 201)
        response_data = response.json()
        self.assertValidFormVersionData(response_data, check_annotated_fields=False)

        created_version = m.FormVersion.objects.get(pk=response_data["id"])
        self.assertEqual(created_version.version_id, "2020022401")
        self.assertIsInstance(created_version.file, File)
        self.assertGreater(created_version.file.size, 100)
        # the file can be with a suffix in case of collision
        # another test create a version with the same file, the db is resetted but not the filesystem
        self.assertRegex(created_version.file.name, r"forms/new_land_speeder_concept_2020022401(.*).xml")
        self.assertIsInstance(created_version.xls_file, File)
        self.assertGreater(created_version.xls_file.size, 100)
        self.assertRegex(created_version.xls_file.name, r"forms/new_land_speeder_concept_2020022401(.*).xlsx")

        version_form = created_version.form
        self.assertEqual("sample1", version_form.form_id)

    def test_form_versions_create_ok_second_version(self):
        """POST /form-versions/ happy path (second version)"""

        self.client.force_authenticate(self.yoda)
        with open("iaso/tests/fixtures/odk_form_valid_sample2_2020022402.xlsx", "rb") as xls_file:
            response = self.client.post(
                f"/api/formversions/",
                data={"form_id": self.form_2.id, "xls_file": xls_file},
                format="multipart",
                headers={"accept": "application/json"},
            )
        self.assertJSONResponse(response, 201)
        response_data = response.json()
        self.assertValidFormVersionData(response_data, check_annotated_fields=False)

        created_version = m.FormVersion.objects.get(pk=response_data["id"])
        self.assertEqual(created_version.version_id, "2020022402")

    def test_form_versions_create_ok_second_version_with_mappings(self):
        """POST /form-versions/ happy path (second version)"""

        self.client.force_authenticate(self.yoda)
        form_mapping = m.Mapping.objects.create(form=self.form_2, mapping_type=m.AGGREGATE, data_source=self.sw_source)
        m.MappingVersion.objects.create(
            mapping=form_mapping,
            form_version=self.form_2.form_versions.first(),
            json={
                "question_mappings": {
                    "old_question": {"type": "neverMapped"},
                    "member": {"id": "dhis2_id", "valueType": "NUMBER"},
                }
            },
        )

        derived_form_mapping = m.Mapping.objects.create(
            form=self.form_2, mapping_type=m.DERIVED, data_source=self.sw_source, name="derived"
        )
        m.MappingVersion.objects.create(
            mapping=derived_form_mapping,
            form_version=self.form_2.form_versions.first(),
            name="derived",
            json={
                "aggregations": [
                    {"id": "old_question", "questionName": "question_name_old", "aggregationType": "sum"},
                    {"id": "member", "questionName": "question_name_member", "aggregationType": "sum"},
                ]
            },
        )

        with open("iaso/tests/fixtures/odk_form_valid_sample2_2020022402.xlsx", "rb") as xls_file:
            response = self.client.post(
                f"/api/formversions/",
                data={"form_id": self.form_2.id, "xls_file": xls_file},
                format="multipart",
                headers={"accept": "application/json"},
            )
        self.assertJSONResponse(response, 201)
        response_data = response.json()
        self.assertValidFormVersionData(response_data, check_annotated_fields=False)

        created_version = m.FormVersion.objects.get(pk=response_data["id"])
        self.assertEqual(created_version.version_id, "2020022402")
        new_mapping = m.MappingVersion.objects.all().filter(mapping__mapping_type=m.AGGREGATE).last()
        self.assertEqual(new_mapping.form_version_id, response_data["id"])
        self.assertEqual(new_mapping.json, {"question_mappings": {"member": {"id": "dhis2_id", "valueType": "NUMBER"}}})

        new_mapping = m.MappingVersion.objects.all().filter(mapping__mapping_type=m.DERIVED).last()

        self.assertEqual(new_mapping.form_version_id, response_data["id"])
        self.assertEqual(
            new_mapping.json,
            {"aggregations": [{"aggregationType": "sum", "id": "member", "questionName": "question_name_member"}]},
        )

    def test_form_versions_create_invalid_xls_form_id_1(self):
        """POST /form-versions/ with a form_id that already exists within the account (for a different form)"""

        self.client.force_authenticate(self.yoda)
        with open("iaso/tests/fixtures/odk_form_valid_sample2_2020022401.xlsx", "rb") as xls_file:
            response = self.client.post(
                f"/api/formversions/",
                data={"form_id": self.form_1.id, "xls_file": xls_file},
                format="multipart",
                headers={"accept": "application/json"},
            )
        self.assertJSONResponse(response, 400)
        self.assertHasError(response.json(), "xls_file", "The form_id is already used in another form.")

    def test_form_versions_create_invalid_xls_form_id_2(self):
        """POST /form-versions/ attempt to create a second version with a different form_id"""

        self.client.force_authenticate(self.yoda)
        with open("iaso/tests/fixtures/odk_form_valid_sample1_2020022402.xlsx", "rb") as xls_file:
            response = self.client.post(
                f"/api/formversions/",
                data={"form_id": self.form_2.id, "xls_file": xls_file},
                format="multipart",
                headers={"accept": "application/json"},
            )
        self.assertJSONResponse(response, 400)
        self.assertHasError(response.json(), "xls_file", "Form id should stay constant across form versions.")

    def test_form_versions_create_invalid_xls_version(self):
        """POST /form-versions/ attempt to create a second version with a version inferior to the previous one"""

        self.client.force_authenticate(self.yoda)
        with open("iaso/tests/fixtures/odk_form_valid_sample2_2020022301.xlsx", "rb") as xls_file:
            response = self.client.post(
                f"/api/formversions/",
                data={"form_id": self.form_2.id, "xls_file": xls_file},
                format="multipart",
                headers={"accept": "application/json"},
            )
        self.assertJSONResponse(response, 400)
        self.assertHasError(
            response.json(), "xls_file", "Invalid XLS file: Parsed version should be greater than previous version."
        )

    def test_form_versions_create_invalid_xls_file(self):
        """POST /form-versions/ with invalid XLS file"""

        self.client.force_authenticate(self.yoda)
        with open("iaso/tests/fixtures/odk_form_blatantly_invalid.xlsx", "rb") as xls_file:
            response = self.client.post(
                f"/api/formversions/",
                data={"form_id": self.form_1.id, "xls_file": xls_file},
                format="multipart",
                headers={"accept": "application/json"},
            )
        self.assertJSONResponse(response, 400)
        self.assertHasError(
            response.json(),
            "xls_file",
            "Invalid XLS file: The survey sheet is either empty or missing important column headers.",
        )

    def test_form_versions_create_no_xls_file(self):
        """POST /form-versions/, missing params"""

        self.client.force_authenticate(self.yoda)
        response = self.client.post(
            f"/api/formversions/", data={}, format="multipart", headers={"accept": "application/json"}
        )
        self.assertJSONResponse(response, 400)
        response_data = response.json()
        self.assertHasError(response_data, "form_id")

    def test_form_versions_create_no_auth(self):
        """POST /form-versions/ , without auth -> we expect a 401 error"""

        with open("iaso/tests/fixtures/odk_form_valid_no_settings.xlsx", "rb") as xls_file:
            response = self.client.post(
                f"/api/formversions/",
                data={"form_id": self.form_1.id, "xls_file": xls_file},
                format="multipart",
                headers={"accept": "application/json"},
            )
        self.assertJSONResponse(response, 401)

    def test_form_versions_create_wrong_form(self):
        """POST /form-versions/ - user has no access to the underlying form"""

        self.client.force_authenticate(self.batman)
        form_file_mock = mock.MagicMock(spec=File)
        form_file_mock.name = "test_batman.xml"
        response = self.client.post(
            f"/api/formversions/",
            data={"form_id": self.form_1.id, "version_id": "february_2020", "xls_file": form_file_mock},
            format="multipart",
        )
        self.assertJSONResponse(response, 400)

    def test_formversions_list_without_auth_for_project_requiring_auth(self):
        """GET /formversions/ without auth for project which requires it: 401"""

        response = self.client.get("/api/formversions/", {APP_ID: self.project.app_id})
        self.assertJSONResponse(response, 401)

    def test_formversions_list_with_wrong_auth_for_project_requiring_auth(self):
        """GET /formversions/ with wrong auth for project which requires it: 401"""

        self.client.force_authenticate(user=self.batman)
        response = self.client.get("/api/formversions/", {APP_ID: self.project.app_id})
        self.assertJSONResponse(response, 401)

    def test_formversions_list_with_auth_for_project_requiring_auth(self):
        """GET /formversions/ with auth for project which requires it: 200"""

        self.client.force_authenticate(user=self.yoda)
        response = self.client.get("/api/formversions/", {APP_ID: self.project.app_id})
        self.assertJSONResponse(response, 200)

    def assertValidFormVersionData(
        self, form_version_data: typing.Mapping, *, check_annotated_fields: bool = True
    ):  # TODO: check for other fields
        self.assertHasField(form_version_data, "id", int)
        self.assertHasField(form_version_data, "file", str)
        self.assertHasField(form_version_data, "xls_file", str)
        self.assertHasField(form_version_data, "version_id", str)
        self.assertHasField(form_version_data, "created_at", float)
        self.assertHasField(form_version_data, "updated_at", float)

        if check_annotated_fields:
            self.assertHasField(form_version_data, "mapped", bool)
            self.assertHasField(form_version_data, "full_name", str)
