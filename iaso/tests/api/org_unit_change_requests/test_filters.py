import datetime

from django.contrib.auth.models import Group
from django.contrib.gis.geos import Point

from iaso import models as m
from iaso.models.payments import PaymentStatuses
from iaso.test import APITestCase


class FilterOrgUnitChangeRequestAPITestCase(APITestCase):
    """
    Test filtering on the ViewSet.
    """

    @classmethod
    def setUpTestData(cls):
        data_source = m.DataSource.objects.create(name="Data source")
        version = m.SourceVersion.objects.create(number=1, data_source=data_source)
        org_unit_type = m.OrgUnitType.objects.create(name="Org unit type")
        org_unit = m.OrgUnit.objects.create(
            org_unit_type=org_unit_type, version=version, uuid="1539f174-4c53-499c-85de-7a58458c49ef"
        )

        account = m.Account.objects.create(name="Account", default_version=version)
        project = m.Project.objects.create(name="Project", account=account, app_id="foo.bar.baz")
        user = cls.create_user_with_profile(username="user", account=account)
        user_with_review_perm = cls.create_user_with_profile(
            username="user_with_review_perm",
            account=account,
            permissions=["iaso_org_unit_change_request_review"],
        )

        data_source.projects.set([project])
        org_unit_type.projects.set([project])
        user.iaso_profile.org_units.set([org_unit])

        cls.account = account
        cls.data_source = data_source
        cls.org_unit = org_unit
        cls.org_unit_type = org_unit_type
        cls.project = project
        cls.user = user
        cls.user_with_review_perm = user_with_review_perm
        cls.version = version

    def test_filterchange_request_on_date_created_from_and_date_created_to(self):
        self.client.force_authenticate(self.user_with_review_perm)
        changeRequest1 = m.OrgUnitChangeRequest.objects.create(
            org_unit=self.org_unit,
            new_name="Foo",
        )
        changeRequest1.created_at = datetime.datetime(2023, 10, 17, 17, 0, 0, 0, tzinfo=datetime.timezone.utc)
        changeRequest1.save()

        changeRequest2 = m.OrgUnitChangeRequest.objects.create(org_unit=self.org_unit, new_name="Bar")
        changeRequest2.created_at = datetime.datetime(2022, 10, 17, 17, 0, 0, 0, tzinfo=datetime.timezone.utc)
        changeRequest2.save()

        response = self.client.get("/api/orgunits/changes/?created_at_after=17-10-2023&created_at_before=17-10-2023")
        self.assertJSONResponse(response, 200)
        self.assertEqual(1, len(response.data["results"]))

        response = self.client.get("/api/orgunits/changes/?created_at_after=17-10-2022")
        self.assertJSONResponse(response, 200)
        self.assertEqual(2, len(response.data["results"]))

        response = self.client.get("/api/orgunits/changes/?created_at_before=17-10-2022")
        self.assertJSONResponse(response, 200)
        self.assertEqual(1, len(response.data["results"]))

    def test_filter_on_forms(self):
        form = m.Form.objects.create(name="Test Form")
        instance = m.Instance.objects.create(
            org_unit=self.org_unit,
            form=form,
            period="202001",
            project=self.project,
        )

        change_request1 = m.OrgUnitChangeRequest.objects.create(org_unit=self.org_unit, new_name="Foo")
        change_request1.new_reference_instances.add(instance)
        change_request2 = m.OrgUnitChangeRequest.objects.create(org_unit=self.org_unit, new_name="Bar")
        change_request2.old_reference_instances.add(instance)

        self.client.force_authenticate(self.user)
        response = self.client.get(f"/api/orgunits/changes/?forms={form.id}")
        self.assertJSONResponse(response, 200)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertIn(change_request1.id, [change["id"] for change in response.data["results"]])
        self.assertIn(change_request2.id, [change["id"] for change in response.data["results"]])

    def test_filter_on_groups(self):
        group1 = m.Group.objects.create(name="Group 1")
        group2 = m.Group.objects.create(name="Group 2")

        # Create change requests with new groups
        change_request1 = m.OrgUnitChangeRequest.objects.create(org_unit=self.org_unit, new_name="Foo")
        change_request1.new_groups.add(group1)

        # Create change requests with old groups
        change_request2 = m.OrgUnitChangeRequest.objects.create(org_unit=self.org_unit, new_name="Bar")
        change_request2.old_groups.add(group2)

        self.client.force_authenticate(self.user)

        # Test filtering by both new and old groups
        response = self.client.get(f"/api/orgunits/changes/?groups={group1.id},{group2.id}")
        self.assertJSONResponse(response, 200)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertIn(change_request1.id, [change["id"] for change in response.data["results"]])
        self.assertIn(change_request2.id, [change["id"] for change in response.data["results"]])

        # Test filtering by new groups only
        response = self.client.get(f"/api/orgunits/changes/?groups={group1.id}")
        self.assertJSONResponse(response, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertIn(change_request1.id, [change["id"] for change in response.data["results"]])
        self.assertNotIn(change_request2.id, [change["id"] for change in response.data["results"]])

        # Test filtering by old groups only
        response = self.client.get(f"/api/orgunits/changes/?groups={group2.id}")
        self.assertJSONResponse(response, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertNotIn(change_request1.id, [change["id"] for change in response.data["results"]])
        self.assertIn(change_request2.id, [change["id"] for change in response.data["results"]])

    def test_filter_on_parent_id(self):
        parent_org_unit = m.OrgUnit.objects.create(name="Parent Org Unit")
        another_parent_org_unit = m.OrgUnit.objects.create(name="Another Parent Org Unit")

        # Create a change request with a new parent
        change_request1 = m.OrgUnitChangeRequest.objects.create(
            org_unit=self.org_unit, new_name="Foo", new_parent=parent_org_unit
        )

        # Create a change request with an old parent
        change_request2 = m.OrgUnitChangeRequest.objects.create(
            org_unit=self.org_unit, new_name="Bar", old_parent=another_parent_org_unit
        )

        change_request2.old_parent = another_parent_org_unit
        change_request2.save()
        self.client.force_authenticate(self.user)

        # Test filtering by new parent
        response = self.client.get(f"/api/orgunits/changes/?parent_id={parent_org_unit.id}")
        self.assertJSONResponse(response, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertIn(change_request1.id, [change["id"] for change in response.data["results"]])
        self.assertNotIn(change_request2.id, [change["id"] for change in response.data["results"]])

        # Test filtering by old parent
        response = self.client.get(f"/api/orgunits/changes/?parent_id={another_parent_org_unit.id}")
        self.assertJSONResponse(response, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertNotIn(change_request1.id, [change["id"] for change in response.data["results"]])
        self.assertIn(change_request2.id, [change["id"] for change in response.data["results"]])

    def test_filter_on_org_unit_type_id(self):
        org_unit_type = m.OrgUnitType.objects.create(name="New Org Unit Type")
        change_request1 = m.OrgUnitChangeRequest.objects.create(
            org_unit=self.org_unit, new_name="Foo", new_org_unit_type=org_unit_type
        )
        change_request2 = m.OrgUnitChangeRequest.objects.create(org_unit=self.org_unit, new_name="Bar")

        self.client.force_authenticate(self.user)
        response = self.client.get(f"/api/orgunits/changes/?org_unit_type_id={org_unit_type.id}")
        self.assertJSONResponse(response, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertIn(change_request1.id, [change["id"] for change in response.data["results"]])
        self.assertNotIn(change_request2.id, [change["id"] for change in response.data["results"]])

    def test_filter_on_users(self):
        another_user = self.create_user_with_profile(username="another_user", account=self.account)
        change_request1 = m.OrgUnitChangeRequest.objects.create(
            org_unit=self.org_unit, new_name="Foo", created_by=another_user
        )
        change_request2 = m.OrgUnitChangeRequest.objects.create(
            org_unit=self.org_unit, new_name="Foo", created_by=self.user
        )

        self.client.force_authenticate(self.user)
        response = self.client.get(f"/api/orgunits/changes/?users={another_user.id}")
        self.assertJSONResponse(response, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertIn(change_request1.id, [change["id"] for change in response.data["results"]])
        self.assertNotIn(change_request2.id, [change["id"] for change in response.data["results"]])

    def test_filter_on_user_roles(self):
        group = Group.objects.create(name="Group")
        user_role = m.UserRole.objects.create(account=self.account, group=group)
        another_user = self.create_user_with_profile(username="another_user", account=self.account)
        self.user.iaso_profile.user_roles.add(user_role)
        change_request1 = m.OrgUnitChangeRequest.objects.create(
            org_unit=self.org_unit, new_name="Foo", created_by=self.user
        )
        change_request2 = m.OrgUnitChangeRequest.objects.create(
            org_unit=self.org_unit, new_name="Foo", created_by=another_user
        )

        self.client.force_authenticate(self.user)
        response = self.client.get(f"/api/orgunits/changes/?user_roles={user_role.id}")
        self.assertJSONResponse(response, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertIn(change_request1.id, [change["id"] for change in response.data["results"]])
        self.assertNotIn(change_request2.id, [change["id"] for change in response.data["results"]])

    def test_filter_on_with_location(self):
        change_request_with_new_location = m.OrgUnitChangeRequest.objects.create(
            org_unit=self.org_unit,
            new_name="Foo",
            new_location=Point(0, 0, 0, srid=4326),
        )
        change_request_with_old_location = m.OrgUnitChangeRequest.objects.create(
            org_unit=self.org_unit,
            new_name="Foo",
        )
        change_request_with_old_location.old_location = Point(0, 0, 0, srid=4326)
        change_request_with_old_location.save()
        change_request_without_location = m.OrgUnitChangeRequest.objects.create(org_unit=self.org_unit, new_name="Bar")

        self.client.force_authenticate(self.user)
        response = self.client.get("/api/orgunits/changes/?with_location=true")
        self.assertJSONResponse(response, 200)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertIn(change_request_with_new_location.id, [change["id"] for change in response.data["results"]])
        self.assertIn(change_request_with_old_location.id, [change["id"] for change in response.data["results"]])

        response = self.client.get("/api/orgunits/changes/?with_location=false")
        self.assertJSONResponse(response, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertIn(change_request_without_location.id, [change["id"] for change in response.data["results"]])

    def test_filter_by_multiple_statuses(self):
        m.OrgUnitChangeRequest.objects.create(
            org_unit=self.org_unit, new_name="New Request", status=m.OrgUnitChangeRequest.Statuses.NEW
        )
        m.OrgUnitChangeRequest.objects.create(
            org_unit=self.org_unit, new_name="Rejected Request", status=m.OrgUnitChangeRequest.Statuses.REJECTED
        )
        m.OrgUnitChangeRequest.objects.create(
            org_unit=self.org_unit, new_name="Approved Request", status=m.OrgUnitChangeRequest.Statuses.APPROVED
        )

        # Authenticate the user with review permissions
        self.client.force_authenticate(self.user_with_review_perm)

        # Test filtering by multiple statuses
        response = self.client.get("/api/orgunits/changes/?status=new,rejected")
        self.assertJSONResponse(response, 200)
        self.assertEqual(len(response.data["results"]), 2)
        result_statuses = {change["status"] for change in response.data["results"]}
        self.assertIn(m.OrgUnitChangeRequest.Statuses.NEW, result_statuses)
        self.assertIn(m.OrgUnitChangeRequest.Statuses.REJECTED, result_statuses)
        self.assertNotIn(m.OrgUnitChangeRequest.Statuses.APPROVED, result_statuses)

    def test_filter_on_payment_status(self):
        # Should not show up, because no payment status
        change_request_new = m.OrgUnitChangeRequest.objects.create(
            org_unit=self.org_unit, new_name="New Request", status=m.OrgUnitChangeRequest.Statuses.NEW
        )

        # Should show when filtering on "PENDING" status
        change_request_approved = m.OrgUnitChangeRequest.objects.create(
            org_unit=self.org_unit, new_name="Approved Request", status=m.OrgUnitChangeRequest.Statuses.APPROVED
        )

        # Should show when filtering on "PENDING" status
        change_request_with_potential_payment = m.OrgUnitChangeRequest.objects.create(
            org_unit=self.org_unit,
            new_name="Approved Request with Potential Payment",
            status=m.OrgUnitChangeRequest.Statuses.APPROVED,
        )
        potential_payment = m.PotentialPayment.objects.create(user=self.user_with_review_perm)
        change_request_with_potential_payment.potential_payment = potential_payment
        change_request_with_potential_payment.save()

        # Should show when filtering on "PAID" status

        change_request_with_payment = m.OrgUnitChangeRequest.objects.create(
            org_unit=self.org_unit,
            new_name="Approved Request with Payment",
            status=m.OrgUnitChangeRequest.Statuses.APPROVED,
        )
        payment = m.Payment.objects.create(user=self.user_with_review_perm, status=PaymentStatuses.PAID.value)
        change_request_with_payment.payment = payment
        change_request_with_payment.save()
        # Authenticate the user
        self.client.force_authenticate(self.user)

        # Test filter on Pending status
        response = self.client.get("/api/orgunits/changes/?payment_status=pending")
        self.assertJSONResponse(response, 200)
        self.assertEqual(len(response.data["results"]), 2)
        result_ids = {change["id"] for change in response.data["results"]}
        self.assertIn(change_request_approved.id, result_ids)
        self.assertIn(change_request_with_potential_payment.id, result_ids)
        self.assertNotIn(change_request_with_payment.id, result_ids)
        self.assertNotIn(change_request_new.id, result_ids)
        # Test filter on PAID status
        response = self.client.get("/api/orgunits/changes/?payment_status=paid")
        self.assertJSONResponse(response, 200)
        self.assertEqual(len(response.data["results"]), 1)
        result_ids = {change["id"] for change in response.data["results"]}
        self.assertIn(change_request_with_payment.id, result_ids)
        self.assertNotIn(change_request_with_potential_payment.id, result_ids)
        self.assertNotIn(change_request_approved.id, result_ids)
        self.assertNotIn(change_request_new.id, result_ids)

    def test_filter_on_data_source_synchronization_id(self):
        change_request = m.OrgUnitChangeRequest.objects.create(org_unit=self.org_unit, new_name="Change request 1")

        version2 = m.SourceVersion.objects.create(number=2, data_source=self.data_source)
        data_source_synchronization = m.DataSourceVersionsSynchronization.objects.create(
            name="Synchronization",
            source_version_to_update=self.version,
            source_version_to_compare_with=version2,
            account=self.account,
            created_by=self.user,
        )
        change_request_with_sync = m.OrgUnitChangeRequest.objects.create(
            org_unit=self.org_unit,
            new_name="Change request 2",
            data_source_synchronization=data_source_synchronization,
        )

        self.client.force_authenticate(self.user)

        response = self.client.get("/api/orgunits/changes/")
        self.assertJSONResponse(response, 200)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(response.data["results"][0]["id"], change_request.pk)
        self.assertEqual(response.data["results"][1]["id"], change_request_with_sync.pk)

        response = self.client.get(
            f"/api/orgunits/changes/?data_source_synchronization_id={data_source_synchronization.pk}"
        )
        self.assertJSONResponse(response, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], change_request_with_sync.pk)

        response = self.client.get(
            f"/api/orgunits/changes/?data_source_synchronization_id={data_source_synchronization.pk + 1}"
        )
        self.assertJSONResponse(response, 200)
        self.assertEqual(response.data["count"], 0)
