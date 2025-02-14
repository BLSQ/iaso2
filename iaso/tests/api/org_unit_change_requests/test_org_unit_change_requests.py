import csv
import datetime
import io

import time_machine

from iaso import models as m
from iaso.api.org_unit_change_requests.views import OrgUnitChangeRequestViewSet
from iaso.tests.tasks.task_api_test_case import TaskAPITestCase
from iaso.utils.models.common import get_creator_name


class OrgUnitChangeRequestAPITestCase(TaskAPITestCase):
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
            org_unit_type=org_unit_type,
            version=version,
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
        cls.org_unit_change_request_csv_columns = OrgUnitChangeRequestViewSet.org_unit_change_request_csv_columns()
        cls.org_unit_type = org_unit_type
        cls.project = project
        cls.user = user
        cls.user_with_review_perm = user_with_review_perm
        cls.version = version

    def test_list_ok(self):
        m.OrgUnitChangeRequest.objects.create(org_unit=self.org_unit, new_name="Foo")
        m.OrgUnitChangeRequest.objects.create(org_unit=self.org_unit, new_name="Bar")

        self.client.force_authenticate(self.user)

        with self.assertNumQueries(12):
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
            # extra field `select_all_count` at the same level as `count` for pagination
            #  11. COUNT(*) -> `self.get_queryset()` is called 2 times…
            #  12. COUNT(status=new)
            response = self.client.get("/api/orgunits/changes/")
            self.assertJSONResponse(response, 200)

        self.assertEqual(2, len(response.data["results"]))
        self.assertEqual(2, response.data["count"])
        self.assertEqual(2, response.data["select_all_count"])

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

    def test_bulk_review_without_perm(self):
        self.client.force_authenticate(self.user)
        response = self.client.patch(f"/api/orgunits/changes/bulk_review/", data={}, format="json")
        self.assertEqual(response.status_code, 403)

    @time_machine.travel(DT, tick=False)
    def test_bulk_review_approve(self):
        self.client.force_authenticate(self.user_with_review_perm)

        change_request_1 = m.OrgUnitChangeRequest.objects.create(
            status=m.OrgUnitChangeRequest.Statuses.NEW, org_unit=self.org_unit, created_by=self.user, new_name="foo"
        )
        change_request_2 = m.OrgUnitChangeRequest.objects.create(
            status=m.OrgUnitChangeRequest.Statuses.NEW, org_unit=self.org_unit, created_by=self.user, new_name="bar"
        )

        data = {
            "select_all": 1,
            "selected_ids": [],
            "unselected_ids": [],
            "status": m.OrgUnitChangeRequest.Statuses.APPROVED,
            "approved_fields": ["new_name"],
        }
        response = self.client.patch(f"/api/orgunits/changes/bulk_review/", data=data, format="json")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        task = self.assertValidTaskAndInDB(data["task"], status="QUEUED", name="org_unit_change_requests_bulk_approve")

        self.assertEqual(task.launcher, self.user_with_review_perm)
        self.assertCountEqual(task.params["kwargs"]["change_requests_ids"], [change_request_1.pk, change_request_2.pk])
        self.assertCountEqual(task.params["kwargs"]["approved_fields"], ["new_name"])

        self.runAndValidateTask(task, "SUCCESS")

        task.refresh_from_db()
        self.assertEqual(task.progress_message, "Bulk approved 2 change requests.")

        change_request_1.refresh_from_db()
        self.assertEqual(change_request_1.status, m.OrgUnitChangeRequest.Statuses.APPROVED)
        self.assertEqual(change_request_1.updated_by, self.user_with_review_perm)

        change_request_2.refresh_from_db()
        self.assertEqual(change_request_2.status, m.OrgUnitChangeRequest.Statuses.APPROVED)
        self.assertEqual(change_request_2.updated_by, self.user_with_review_perm)

    @time_machine.travel(DT, tick=False)
    def test_bulk_review_reject(self):
        self.client.force_authenticate(self.user_with_review_perm)

        change_request_1 = m.OrgUnitChangeRequest.objects.create(
            status=m.OrgUnitChangeRequest.Statuses.NEW, org_unit=self.org_unit, created_by=self.user, new_name="foo"
        )
        change_request_2 = m.OrgUnitChangeRequest.objects.create(
            status=m.OrgUnitChangeRequest.Statuses.NEW, org_unit=self.org_unit, created_by=self.user, new_name="bar"
        )
        change_request_3 = m.OrgUnitChangeRequest.objects.create(
            status=m.OrgUnitChangeRequest.Statuses.NEW, org_unit=self.org_unit, created_by=self.user, new_name="baz"
        )

        data = {
            "select_all": 0,
            "selected_ids": [change_request_1.pk, change_request_2.pk],
            "unselected_ids": [change_request_3.pk],
            "status": m.OrgUnitChangeRequest.Statuses.REJECTED,
            "approved_fields": [],
            "rejection_comment": "No way.",
        }
        response = self.client.patch(f"/api/orgunits/changes/bulk_review/", data=data, format="json")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        task = self.assertValidTaskAndInDB(data["task"], status="QUEUED", name="org_unit_change_requests_bulk_reject")

        self.assertEqual(task.launcher, self.user_with_review_perm)
        self.assertCountEqual(task.params["kwargs"]["change_requests_ids"], [change_request_1.pk, change_request_2.pk])
        self.assertCountEqual(task.params["kwargs"]["rejection_comment"], "No way.")

        self.runAndValidateTask(task, "SUCCESS")

        task.refresh_from_db()
        self.assertEqual(task.progress_message, "Bulk rejected 2 change requests.")

        change_request_1.refresh_from_db()
        self.assertEqual(change_request_1.status, m.OrgUnitChangeRequest.Statuses.REJECTED)
        self.assertEqual(change_request_1.updated_by, self.user_with_review_perm)

        change_request_2.refresh_from_db()
        self.assertEqual(change_request_2.status, m.OrgUnitChangeRequest.Statuses.REJECTED)
        self.assertEqual(change_request_2.updated_by, self.user_with_review_perm)

        change_request_3.refresh_from_db()
        self.assertEqual(change_request_3.status, m.OrgUnitChangeRequest.Statuses.NEW)
        self.assertEqual(change_request_3.updated_by, None)

    def test_export_to_csv(self):
        """
        It tests the CSV export for the org change requests list.
        """
        change_request = m.OrgUnitChangeRequest.objects.create(org_unit=self.org_unit, new_name="Foo")
        m.OrgUnitChangeRequest.objects.create(org_unit=self.org_unit, new_name="Bar")

        self.client.force_authenticate(self.user)

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
        self.assertEqual(len(data), 3)

        data_headers = data[0]
        self.assertEqual(
            data_headers,
            self.org_unit_change_request_csv_columns,
        )

        first_data_row = data[1]
        expected_row_data = [
            str(change_request.id),
            change_request.org_unit.name,
            change_request.org_unit.parent.name if change_request.org_unit.parent else "",
            change_request.org_unit.org_unit_type.name,
            ",".join(group.name for group in change_request.org_unit.groups.all()),
            str(change_request.get_status_display()),
            datetime.datetime.strftime(change_request.created_at, "%Y-%m-%d"),
            get_creator_name(change_request.created_by) if change_request.created_by else "",
            datetime.datetime.strftime(change_request.updated_at, "%Y-%m-%d"),
            get_creator_name(change_request.updated_by) if change_request.updated_by else "",
        ]
        self.assertEqual(
            first_data_row,
            expected_row_data,
        )
