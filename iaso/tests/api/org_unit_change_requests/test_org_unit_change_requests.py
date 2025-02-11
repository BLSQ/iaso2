import csv
import datetime
import io

from iaso.api.org_unit_change_requests.views import OrgUnitChangeRequestViewSet
from iaso.utils.models.common import get_creator_name
import time_machine

from iaso.test import APITestCase
from iaso import models as m


class OrgUnitChangeRequestAPITestCase(APITestCase):
    """
    Test actions on the ViewSet.
    """

    DT = datetime.datetime(2023, 10, 17, 17, 0, 0, 0, tzinfo=datetime.timezone.utc)

    @classmethod
    def setUpTestData(cls):
        data_source = m.DataSource.objects.create(name="Data source")
        version = m.SourceVersion.objects.create(number=1, data_source=data_source)
        org_unit_type = m.OrgUnitType.objects.create(name="Org unit type")
        org_unit = m.OrgUnit.objects.create(
            name="Org unit",
            org_unit_type=org_unit_type,
            version=version,
            source_ref="112244",
            uuid="1539f174-4c53-499c-85de-7a58458c49ef",
            closed_date=cls.DT.date(),
        )

        # Create a bunch of related objects. This is useful to detect N+1.
        group_1 = m.Group.objects.create(name="Group 1", source_version=version)
        group_2 = m.Group.objects.create(name="Group 2", source_version=version)
        group_3 = m.Group.objects.create(name="Group 3", source_version=version)
        org_unit.groups.add(group_1, group_2, group_3)

        form_1 = m.Form.objects.create(name="Form 1")
        form_2 = m.Form.objects.create(name="Form 2")
        form_3 = m.Form.objects.create(name="Form 3")
        instance_1 = m.Instance.objects.create(form=form_1, org_unit=org_unit)
        instance_2 = m.Instance.objects.create(form=form_2, org_unit=org_unit)
        instance_3 = m.Instance.objects.create(form=form_3, org_unit=org_unit)
        m.OrgUnitReferenceInstance.objects.create(org_unit=org_unit, form=form_1, instance=instance_1)
        m.OrgUnitReferenceInstance.objects.create(org_unit=org_unit, form=form_2, instance=instance_2)
        m.OrgUnitReferenceInstance.objects.create(org_unit=org_unit, form=form_3, instance=instance_3)

        account = m.Account.objects.create(name="Account", default_version=version)
        project = m.Project.objects.create(name="Project", account=account, app_id="foo.bar.baz")
        user = cls.create_user_with_profile(username="user", account=account)
        user_with_review_perm = cls.create_user_with_profile(
            username="user_with_review_perm", account=account, permissions=["iaso_org_unit_change_request_review"]
        )

        data_source.projects.set([project])
        org_unit_type.projects.set([project])
        user.iaso_profile.org_units.set([org_unit])

        cls.form_3 = form_3
        cls.instance_1 = instance_1
        cls.instance_2 = instance_2
        cls.instance_3 = instance_3
        cls.org_unit = org_unit
        cls.org_unit_type = org_unit_type
        cls.project = project
        cls.user = user
        cls.user_with_review_perm = user_with_review_perm
        cls.version = version

    def test_list_ok(self):
        m.OrgUnitChangeRequest.objects.create(org_unit=self.org_unit, new_name="Foo")
        m.OrgUnitChangeRequest.objects.create(org_unit=self.org_unit, new_name="Bar")

        self.client.force_authenticate(self.user)

        with self.assertNumQueries(10):
            # filter_for_user_and_app_id
            #   1. SELECT OrgUnit
            # get_queryset
            #   2. COUNT(*)
            #   3. SELECT OrgUnitChangeRequest
            # prefetch
            #   4. PREFETCH OrgUnit.groups
            #   5. PREFETCH OrgUnit.reference_instances__form
            #   6. PREFETCH OrgUnitChangeRequest.new_groups
            #   7. PREFETCH OrgUnitChangeRequest.old_groups
            #   8. PREFETCH OrgUnitChangeRequest.new_reference_instances__form
            #   9. PREFETCH OrgUnitChangeRequest.old_reference_instances__form
            #  10. PREFETCH OrgUnitChangeRequest.org_unit_type.projects
            response = self.client.get("/api/orgunits/changes/")
            self.assertJSONResponse(response, 200)
            self.assertEqual(2, len(response.data["results"]))

    def test_list_without_auth(self):
        response = self.client.get("/api/orgunits/changes/")
        self.assertJSONResponse(response, 401)

    def test_retrieve_ok(self):
        change_request = m.OrgUnitChangeRequest.objects.create(org_unit=self.org_unit, new_name="Foo")
        self.client.force_authenticate(self.user)
        with self.assertNumQueries(9):
            response = self.client.get(f"/api/orgunits/changes/{change_request.pk}/")
        self.assertJSONResponse(response, 200)
        self.assertEqual(response.data["id"], change_request.pk)

    def test_retrieve_should_not_include_soft_deleted_intances(self):
        change_request = m.OrgUnitChangeRequest.objects.create(org_unit=self.org_unit, new_name="Foo")
        change_request.new_reference_instances.set([self.instance_1.pk])
        change_request.old_reference_instances.set([self.instance_2.pk])

        m.OrgUnitReferenceInstance.objects.filter(org_unit=self.org_unit).delete()
        m.OrgUnitReferenceInstance.objects.create(org_unit=self.org_unit, form=self.form_3, instance=self.instance_3)

        self.client.force_authenticate(self.user)

        with self.assertNumQueries(9):
            response = self.client.get(f"/api/orgunits/changes/{change_request.pk}/")
            self.assertJSONResponse(response, 200)
            self.assertEqual(response.data["id"], change_request.pk)
            self.assertEqual(len(response.data["new_reference_instances"]), 1)
            self.assertEqual(response.data["new_reference_instances"][0]["id"], self.instance_1.pk)
            self.assertEqual(len(response.data["old_reference_instances"]), 1)
            self.assertEqual(response.data["old_reference_instances"][0]["id"], self.instance_2.pk)
            self.assertEqual(len(response.data["org_unit"]["reference_instances"]), 1)
            self.assertEqual(response.data["org_unit"]["reference_instances"][0]["id"], self.instance_3.pk)

        # Soft delete instances.
        self.instance_1.deleted = True
        self.instance_1.save()
        self.instance_2.deleted = True
        self.instance_2.save()
        self.instance_3.deleted = True
        self.instance_3.save()

        with self.assertNumQueries(9):
            response = self.client.get(f"/api/orgunits/changes/{change_request.pk}/")
            self.assertJSONResponse(response, 200)
            self.assertEqual(response.data["id"], change_request.pk)
            self.assertEqual(len(response.data["new_reference_instances"]), 0)
            self.assertEqual(len(response.data["old_reference_instances"]), 0)
            self.assertEqual(len(response.data["org_unit"]["reference_instances"]), 0)

    def test_retrieve_without_auth(self):
        change_request = m.OrgUnitChangeRequest.objects.create(org_unit=self.org_unit, new_name="Foo")
        response = self.client.get(f"/api/orgunits/changes/{change_request.pk}/")
        self.assertJSONResponse(response, 401)

    @time_machine.travel(DT, tick=False)
    def test_create_ok(self):
        self.client.force_authenticate(self.user)
        data = {
            "org_unit_id": self.org_unit.id,
            "new_name": "I want this new name",
            "new_org_unit_type_id": self.org_unit_type.pk,
        }
        response = self.client.post("/api/orgunits/changes/", data=data, format="json")
        self.assertEqual(response.status_code, 201)
        change_request = m.OrgUnitChangeRequest.objects.get(new_name=data["new_name"])
        self.assertEqual(change_request.new_name, data["new_name"])
        self.assertEqual(change_request.new_org_unit_type, self.org_unit_type)
        self.assertEqual(change_request.created_at, self.DT)
        self.assertEqual(change_request.created_by, self.user)
        self.assertEqual(change_request.updated_at, self.DT)
        self.assertEqual(change_request.requested_fields, ["new_name", "new_org_unit_type"])

    @time_machine.travel(DT, tick=False)
    def test_create_ok_erase_fields(self):
        self.client.force_authenticate(self.user)
        data = {
            "org_unit_id": self.org_unit.id,
            "new_parent_id": None,
            "new_name": "",
            "new_groups": [],
            "new_location": None,
            "new_location_accuracy": None,
            "new_org_unit_type_id": self.org_unit_type.pk,  # At least one field is required to create a change request.
            "new_opening_date": None,
            "new_closed_date": None,
            "new_reference_instances": [],
        }
        response = self.client.post("/api/orgunits/changes/", data=data, format="json")
        self.assertEqual(response.status_code, 201)
        change_request = m.OrgUnitChangeRequest.objects.get(new_name=data["new_name"])
        self.assertEqual(change_request.new_name, "")
        self.assertEqual(change_request.new_groups.count(), 0)
        self.assertEqual(change_request.new_location, None)
        self.assertEqual(change_request.new_location_accuracy, None)
        self.assertEqual(change_request.new_org_unit_type, self.org_unit_type)
        self.assertEqual(change_request.new_opening_date, None)
        self.assertEqual(change_request.new_closed_date, None)
        self.assertEqual(change_request.new_reference_instances.count(), 0)
        self.assertEqual(change_request.created_at, self.DT)
        self.assertEqual(change_request.created_by, self.user)
        self.assertEqual(change_request.updated_at, self.DT)
        self.assertEqual(
            change_request.requested_fields,
            [
                "new_parent",
                "new_name",
                "new_org_unit_type",
                "new_groups",
                "new_location",
                "new_location_accuracy",
                "new_opening_date",
                "new_closed_date",
                "new_reference_instances",
            ],
        )

    @time_machine.travel(DT, tick=False)
    def test_create_ok_using_uuid_as_for_org_unit_id(self):
        self.client.force_authenticate(self.user)
        data = {
            "org_unit_id": self.org_unit.uuid,
            "new_name": "I want this new name",
            "new_org_unit_type_id": self.org_unit_type.pk,
        }
        with self.assertNumQueries(11):
            response = self.client.post("/api/orgunits/changes/", data=data, format="json")
        self.assertEqual(response.status_code, 201)
        change_request = m.OrgUnitChangeRequest.objects.get(new_name=data["new_name"])
        self.assertEqual(change_request.new_name, data["new_name"])
        self.assertEqual(change_request.new_org_unit_type, self.org_unit_type)
        self.assertEqual(change_request.created_at, self.DT)
        self.assertEqual(change_request.created_by, self.user)
        self.assertEqual(change_request.updated_at, self.DT)
        self.assertEqual(change_request.requested_fields, ["new_name", "new_org_unit_type"])

    @time_machine.travel(DT, tick=False)
    def test_create_ok_from_mobile(self):
        """
        The mobile adds `?app_id=.bar.baz` in the query params.
        """
        self.client.force_authenticate(self.user)
        data = {
            "uuid": "e05933f4-8370-4329-8cf5-197941785a24",
            "org_unit_id": self.org_unit.id,
            "new_name": "Bar",
        }
        with self.assertNumQueries(12):
            response = self.client.post("/api/orgunits/changes/?app_id=foo.bar.baz", data=data, format="json")
        self.assertEqual(response.status_code, 201)
        change_request = m.OrgUnitChangeRequest.objects.get(uuid=data["uuid"])
        self.assertEqual(change_request.new_name, data["new_name"])
        self.assertEqual(change_request.created_at, self.DT)
        self.assertEqual(change_request.created_by, self.user)
        self.assertEqual(change_request.updated_at, self.DT)
        self.assertEqual(change_request.requested_fields, ["new_name"])

    def test_create_without_auth(self):
        data = {
            "uuid": "e05933f4-8370-4329-8cf5-197941785a24",
            "org_unit_id": self.org_unit.id,
            "new_name": "Foo",
        }
        response = self.client.post("/api/orgunits/changes/", data=data, format="json")
        self.assertJSONResponse(response, 401)

    def test_create_without_perm(self):
        self.client.force_authenticate(self.user)

        unauthorized_org_unit = m.OrgUnit.objects.create()
        data = {
            "org_unit_id": unauthorized_org_unit.id,
            "new_name": "I want this new name",
        }
        response = self.client.post("/api/orgunits/changes/", data=data, format="json")
        self.assertEqual(response.status_code, 403)

    def test_partial_update_without_perm(self):
        self.client.force_authenticate(self.user)

        kwargs = {
            "status": m.OrgUnitChangeRequest.Statuses.NEW,
            "org_unit": self.org_unit,
            "new_name": "Foo",
        }
        change_request = m.OrgUnitChangeRequest.objects.create(**kwargs)

        data = {
            "status": change_request.Statuses.REJECTED,
            "rejection_comment": "Not good enough.",
        }
        response = self.client.patch(f"/api/orgunits/changes/{change_request.pk}/", data=data, format="json")
        self.assertEqual(response.status_code, 403)

    @time_machine.travel(DT, tick=False)
    def test_partial_update_reject(self):
        self.client.force_authenticate(self.user_with_review_perm)

        kwargs = {
            "status": m.OrgUnitChangeRequest.Statuses.NEW,
            "org_unit": self.org_unit,
            "created_by": self.user,
            "new_name": "Foo",
        }
        change_request = m.OrgUnitChangeRequest.objects.create(**kwargs)

        data = {
            "status": change_request.Statuses.REJECTED,
            "rejection_comment": "Not good enough.",
        }
        response = self.client.patch(f"/api/orgunits/changes/{change_request.pk}/", data=data, format="json")
        self.assertEqual(response.status_code, 200)

        change_request.refresh_from_db()
        self.assertEqual(change_request.status, change_request.Statuses.REJECTED)
        self.org_unit.refresh_from_db()
        self.assertEqual(self.org_unit.validation_status, m.OrgUnit.VALIDATION_REJECTED)

    @time_machine.travel(DT, tick=False)
    def test_partial_update_approve(self):
        self.client.force_authenticate(self.user_with_review_perm)

        kwargs = {
            "org_unit": self.org_unit,
            "created_by": self.user,
            "new_name": "Foo",
            "new_closed_date": None,
        }
        change_request = m.OrgUnitChangeRequest.objects.create(**kwargs)

        data = {
            "status": change_request.Statuses.APPROVED,
            "approved_fields": ["new_name", "new_closed_date"],
        }
        response = self.client.patch(f"/api/orgunits/changes/{change_request.pk}/", data=data, format="json")
        self.assertEqual(response.status_code, 200)

        change_request.refresh_from_db()
        self.assertEqual(change_request.status, change_request.Statuses.APPROVED)
        self.org_unit.refresh_from_db()
        self.assertEqual(self.org_unit.name, "Foo")
        self.assertIsNone(self.org_unit.closed_date)
        self.assertEqual(self.org_unit.validation_status, m.OrgUnit.VALIDATION_VALID)

    def test_partial_update_approve_fail_wrong_status(self):
        self.client.force_authenticate(self.user_with_review_perm)

        kwargs = {
            "status": m.OrgUnitChangeRequest.Statuses.APPROVED,
            "org_unit": self.org_unit,
            "approved_fields": ["new_name"],
        }
        change_request = m.OrgUnitChangeRequest.objects.create(**kwargs)

        data = {
            "status": change_request.Statuses.APPROVED,
            "approved_fields": ["new_name"],
        }
        response = self.client.patch(f"/api/orgunits/changes/{change_request.pk}/", data=data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Status must be `new` but current status is `approved`.", response.content.decode())

    def test_update_should_be_forbidden(self):
        self.client.force_authenticate(self.user_with_review_perm)
        change_request = m.OrgUnitChangeRequest.objects.create(org_unit=self.org_unit, new_name="Foo")
        data = {"new_name": "Baz"}
        response = self.client.put(f"/api/orgunits/changes/{change_request.pk}/", data=data, format="json")
        self.assertEqual(response.status_code, 405)

    def test_delete_should_be_forbidden(self):
        self.client.force_authenticate(self.user_with_review_perm)
        change_request = m.OrgUnitChangeRequest.objects.create(org_unit=self.org_unit, new_name="Foo")
        response = self.client.delete(f"/api/orgunits/changes/{change_request.pk}/", format="json")
        self.assertEqual(response.status_code, 405)

    def test_export_to_csv(self):
        """
        It tests the CSV export for the org change requests list.
        """
        self.client.force_authenticate(self.user)

        # Burkina pyramid.
        burkina = m.OrgUnit.objects.create(
            name="Burkina Faso",
            source_ref="11111",
            org_unit_type=m.OrgUnitType.objects.create(category="COUNTRY"),
            validation_status=m.OrgUnit.VALIDATION_VALID,
            path=["1"],
            version=self.version,
        )
        burkina_region = m.OrgUnit.objects.create(
            name="Boucle du Mouhon",
            source_ref="22222",
            parent=burkina,
            org_unit_type=m.OrgUnitType.objects.create(category="REGION"),
            validation_status=m.OrgUnit.VALIDATION_VALID,
            path=["1", "2"],
            version=self.version,
        )
        burkina_district = m.OrgUnit.objects.create(
            name="Banwa",
            source_ref="33333",
            parent=burkina_region,
            org_unit_type=m.OrgUnitType.objects.create(category="DISTRICT"),
            validation_status=m.OrgUnit.VALIDATION_VALID,
            path=["1", "2", "3"],
            version=self.version,
        )
        burkina_district.calculate_paths()

        self.user.iaso_profile.org_units.add(burkina, burkina_region, burkina_district)

        # Create change requests.
        change_request = m.OrgUnitChangeRequest.objects.create(org_unit=burkina_district, new_name="Foo")
        m.OrgUnitChangeRequest.objects.create(org_unit=burkina_region, new_name="Bar")
        m.OrgUnitChangeRequest.objects.create(org_unit=burkina, new_name="Baz")
        m.OrgUnitChangeRequest.objects.create(org_unit=self.org_unit, new_name="Qux")

        with self.assertNumQueries(9):
            response = self.client.get("/api/orgunits/changes/export_to_csv/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get("Content-Disposition"),
            "attachment; filename=review-change-proposals--" + datetime.datetime.now().strftime("%Y-%m-%d") + ".csv",
        )

        response_csv = response.getvalue().decode("utf-8")
        response_string = "".join(s for s in response_csv)
        reader = csv.reader(io.StringIO(response_string), delimiter=",")

        data = list(reader)
        self.assertEqual(len(data), 5)

        data_headers = data[0]
        self.assertEqual(data_headers, OrgUnitChangeRequestViewSet.CSV_HEADER_COLUMNS)

        first_data_row = data[1]
        expected_first_data_row = {
            "Id": str(change_request.id),
            "Org unit ID": str(change_request.org_unit_id),
            "Org unit external reference": "33333",
            "New name": change_request.org_unit.name,
            "New parent": change_request.org_unit.parent.name if change_request.org_unit.parent else "",
            "New org unit type": change_request.org_unit.org_unit_type.name,
            "New groups": ",".join(group.name for group in change_request.org_unit.groups.all()),
            "New status": str(change_request.get_status_display()),
            "Current parent 1": "Boucle du Mouhon",
            "Current parent 2": "Burkina Faso",
            "Current parent 3": "",
            "Current parent 4": "",
            "Ref ext current parent 1": "22222",
            "Ref ext current parent 2": "11111",
            "Ref ext current parent 3": "",
            "Ref ext current parent 4": "",
            "Created": datetime.datetime.strftime(change_request.created_at, "%Y-%m-%d"),
            "Created by": get_creator_name(change_request.created_by) if change_request.created_by else "",
            "Updated": datetime.datetime.strftime(change_request.updated_at, "%Y-%m-%d"),
            "Updated by": get_creator_name(change_request.updated_by) if change_request.updated_by else "",
        }
        self.assertEqual(first_data_row, list(expected_first_data_row.values()))
