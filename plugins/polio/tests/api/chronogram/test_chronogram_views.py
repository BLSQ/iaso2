import datetime

import time_machine

from hat.menupermissions import models as iaso_permission

from iaso import models as m
from iaso.test import APITestCase

from plugins.polio.models import Campaign, Round, Chronogram, ChronogramTask, CampaignType
from plugins.polio.models.chronogram import Period, ChronogramTemplateTask


TODAY = datetime.datetime(2024, 6, 27, 14, 0, 0, 0, tzinfo=datetime.timezone.utc)


@time_machine.travel(TODAY, tick=False)
class ChronogramTaskViewSetTestCase(APITestCase):
    """
    Test ChronogramTaskViewSet.
    """

    @classmethod
    def setUpTestData(cls):
        cls.data_source = m.DataSource.objects.create(name="Data Source")
        cls.source_version = m.SourceVersion.objects.create(data_source=cls.data_source, number=1)
        cls.account = m.Account.objects.create(name="Account", default_version=cls.source_version)
        cls.user = cls.create_user_with_profile(
            email="john@polio.org",
            username="john",
            first_name="John",
            last_name="Doe",
            account=cls.account,
            permissions=[iaso_permission._POLIO_CHRONOGRAM],
        )
        cls.user_with_restricted_write_perms = cls.create_user_with_profile(
            email="kevin@polio.org",
            username="kevin",
            first_name="Kevin",
            last_name="Walsh",
            account=cls.account,
            permissions=[iaso_permission._POLIO_CHRONOGRAM_RESTRICTED_WRITE],
        )

        cls.campaign = Campaign.objects.create(obr_name="Campaign OBR name", account=cls.account)
        cls.polio_type = CampaignType.objects.get(name=CampaignType.POLIO)
        cls.campaign.campaign_types.add(cls.polio_type)

        cls.round = Round.objects.create(number=1, campaign=cls.campaign, started_at=TODAY.date())

        cls.chronogram = Chronogram.objects.create(round=cls.round, created_by=cls.user)
        cls.chronogram_task = ChronogramTask.objects.create(
            period=Period.BEFORE,
            chronogram=cls.chronogram,
            description_en="Ordering markers",
            description_fr="Assurer la commande des marqueurs",
            start_offset_in_days=0,
            user_in_charge="John Doe",
            comment="Comment",
        )

    def test_get_without_auth(self):
        response = self.client.get(f"/api/polio/chronograms/tasks/{self.chronogram_task.pk}/")
        self.assertJSONResponse(response, 401)

    def test_get_without_perm(self):
        self.user.user_permissions.clear()
        self.client.force_authenticate(self.user)
        response = self.client.get(f"/api/polio/chronograms/tasks/{self.chronogram_task.pk}/")
        self.assertJSONResponse(response, 403)

    def test_get_ok(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(f"/api/polio/chronograms/tasks/{self.chronogram_task.pk}/")
        self.assertJSONResponse(response, 200)

    def test_create_ok(self):
        self.client.force_authenticate(self.user)
        data = {
            "chronogram": self.chronogram.pk,
            "period": Period.AFTER,
            "description_en": "Baz EN",
            "description_fr": "Baz FR",
            "start_offset_in_days": 0,
            "status": ChronogramTask.Status.IN_PROGRESS,
            "user_in_charge": "John Doe",
            "comment": "Comment",
        }
        response = self.client.post("/api/polio/chronograms/tasks/", data=data, format="json")
        self.assertEqual(response.status_code, 201)

        chronogram_task = ChronogramTask.objects.get(pk=response.data["id"])
        self.assertEqual(chronogram_task.period, "AFTER")
        self.assertEqual(chronogram_task.description_en, "Baz EN")
        self.assertEqual(chronogram_task.description_fr, "Baz FR")
        self.assertEqual(chronogram_task.start_offset_in_days, 0)
        self.assertEqual(chronogram_task.user_in_charge, "John Doe")
        self.assertEqual(chronogram_task.comment, "Comment")
        self.assertEqual(chronogram_task.created_by, self.user)
        self.assertEqual(chronogram_task.created_at, TODAY)
        self.assertEqual(chronogram_task.updated_by, None)
        self.assertEqual(chronogram_task.created_at, TODAY)
        self.assertEqual(self.chronogram_task.deleted_at, None)

    def test_update_ok(self):
        self.client.force_authenticate(self.user)
        data = {
            "period": Period.AFTER,
            "description_en": "New description",
            "start_offset_in_days": 10,
            "status": ChronogramTask.Status.DONE,
            "comment": "New comment",
        }

        response = self.client.patch(
            f"/api/polio/chronograms/tasks/{self.chronogram_task.pk}/", data=data, format="json"
        )
        self.assertEqual(response.status_code, 200)

        self.chronogram_task.refresh_from_db()
        self.assertEqual(self.chronogram_task.period, "AFTER")
        self.assertEqual(self.chronogram_task.description_en, "New description")
        self.assertEqual(self.chronogram_task.start_offset_in_days, 10)
        self.assertEqual(self.chronogram_task.status, "DONE")
        self.assertEqual(self.chronogram_task.comment, "New comment")
        self.assertEqual(self.chronogram_task.updated_by, self.user)
        self.assertEqual(self.chronogram_task.deleted_at, None)

    def test_update_restricted_ok(self):
        self.client.force_authenticate(self.user_with_restricted_write_perms)
        data = {
            "period": Period.AFTER,
            "description_en": "New description",
            "start_offset_in_days": 10,
            "status": ChronogramTask.Status.DONE,
            "comment": "Restricted user should be able to comment.",
        }

        response = self.client.patch(
            f"/api/polio/chronograms/tasks/{self.chronogram_task.pk}/", data=data, format="json"
        )
        self.assertEqual(response.status_code, 200)

        self.chronogram_task.refresh_from_db()
        # The following fields should be read-only and keep their old values.
        self.assertEqual(self.chronogram_task.period, "BEFORE")
        self.assertEqual(self.chronogram_task.description_en, "Ordering markers")
        self.assertEqual(self.chronogram_task.start_offset_in_days, 0)
        # The following fields should have been changed.
        self.assertEqual(self.chronogram_task.status, "DONE")
        self.assertEqual(self.chronogram_task.comment, "Restricted user should be able to comment.")
        # Meta data.
        self.assertEqual(self.chronogram_task.updated_by, self.user_with_restricted_write_perms)
        self.assertEqual(self.chronogram_task.deleted_at, None)

    def test_soft_delete_ok(self):
        self.client.force_authenticate(self.user)
        response = self.client.delete(f"/api/polio/chronograms/tasks/{self.chronogram_task.pk}/")
        self.assertEqual(response.status_code, 204)

        self.chronogram_task.refresh_from_db()
        self.assertEqual(self.chronogram_task.deleted_at, TODAY)  # Soft deleted.

    def test_for_user_with_restricted_access(self):
        self.client.force_authenticate(self.user_with_restricted_write_perms)
        response = self.client.get(f"/api/polio/chronograms/tasks/{self.chronogram_task.pk}/")
        self.assertJSONResponse(response, 200)

        response = self.client.post("/api/polio/chronograms/tasks/", data={}, format="json")
        self.assertEqual(response.status_code, 403)

        response = self.client.delete(f"/api/polio/chronograms/tasks/{self.chronogram_task.pk}/")
        self.assertEqual(response.status_code, 403)

        self.client.logout()


@time_machine.travel(TODAY, tick=False)
class ChronogramTemplateTaskViewSetTestCase(APITestCase):
    """
    Test ChronogramTemplateTask.
    """

    @classmethod
    def setUpTestData(cls):
        cls.data_source = m.DataSource.objects.create(name="Data Source")
        cls.source_version = m.SourceVersion.objects.create(data_source=cls.data_source, number=1)
        cls.account = m.Account.objects.create(name="Account", default_version=cls.source_version)
        cls.user = cls.create_user_with_profile(
            email="john@polio.org",
            username="john",
            first_name="John",
            last_name="Doe",
            account=cls.account,
            permissions=[iaso_permission._POLIO_CHRONOGRAM],
        )
        cls.user_with_restricted_write_perms = cls.create_user_with_profile(
            email="kevin@polio.org",
            username="kevin",
            first_name="Kevin",
            last_name="Walsh",
            account=cls.account,
            permissions=[iaso_permission._POLIO_CHRONOGRAM_RESTRICTED_WRITE],
        )
        cls.chronogram_template_task = ChronogramTemplateTask.objects.create(
            account=cls.account,
            period=Period.BEFORE,
            description_en="Ordering markers",
            description_fr="Assurer la commande des marqueurs",
            start_offset_in_days=0,
            created_by=cls.user,
        )

    def test_get_without_auth(self):
        response = self.client.get(f"/api/polio/chronograms/template_tasks/{self.chronogram_template_task.pk}/")
        self.assertJSONResponse(response, 401)

    def test_get_without_perm(self):
        self.user.user_permissions.clear()
        self.client.force_authenticate(self.user)
        response = self.client.get(f"/api/polio/chronograms/template_tasks/{self.chronogram_template_task.pk}/")
        self.assertJSONResponse(response, 403)

    def test_get_ok(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(f"/api/polio/chronograms/template_tasks/{self.chronogram_template_task.pk}/")
        self.assertJSONResponse(response, 200)

    def test_create_ok(self):
        self.client.force_authenticate(self.user)
        data = {
            "account": self.account.pk,
            "period": Period.DURING,
            "description_en": "Description EN",
            "description_fr": "Description FR",
            "start_offset_in_days": 5,
        }
        response = self.client.post("/api/polio/chronograms/template_tasks/", data=data, format="json")
        self.assertEqual(response.status_code, 201)

        chronogram_template_task = ChronogramTemplateTask.objects.get(pk=response.data["id"])
        self.assertEqual(chronogram_template_task.account, self.account)
        self.assertEqual(chronogram_template_task.period, "DURING")
        self.assertEqual(chronogram_template_task.description_en, "Description EN")
        self.assertEqual(chronogram_template_task.description_fr, "Description FR")
        self.assertEqual(chronogram_template_task.start_offset_in_days, 5)
        self.assertEqual(chronogram_template_task.created_by, self.user)
        self.assertEqual(chronogram_template_task.created_at, TODAY)
        self.assertEqual(chronogram_template_task.updated_by, None)
        self.assertEqual(chronogram_template_task.deleted_at, None)

    def test_update_ok(self):
        self.client.force_authenticate(self.user)
        data = {
            "period": Period.AFTER,
            "description_en": "New template description EN",
            "description_fr": "New template description FR",
            "start_offset_in_days": 10,
        }

        response = self.client.patch(
            f"/api/polio/chronograms/template_tasks/{self.chronogram_template_task.pk}/", data=data, format="json"
        )
        self.assertEqual(response.status_code, 200)

        self.chronogram_template_task.refresh_from_db()
        self.assertEqual(self.chronogram_template_task.account, self.account)
        self.assertEqual(self.chronogram_template_task.period, "AFTER")
        self.assertEqual(self.chronogram_template_task.description_en, "New template description EN")
        self.assertEqual(self.chronogram_template_task.description_fr, "New template description FR")
        self.assertEqual(self.chronogram_template_task.start_offset_in_days, 10)
        self.assertEqual(self.chronogram_template_task.created_by, self.user)
        self.assertEqual(self.chronogram_template_task.created_at, TODAY)
        self.assertEqual(self.chronogram_template_task.updated_by, self.user)
        self.assertEqual(self.chronogram_template_task.deleted_at, None)

    def test_soft_delete_ok(self):
        self.client.force_authenticate(self.user)
        response = self.client.delete(f"/api/polio/chronograms/template_tasks/{self.chronogram_template_task.pk}/")
        self.assertEqual(response.status_code, 204)

        self.chronogram_template_task.refresh_from_db()
        self.assertEqual(self.chronogram_template_task.deleted_at, TODAY)  # Soft deleted.

    def test_for_user_with_restricted_access(self):
        """
        A user with restricted write permission should not have access to chronogram templates.
        """
        self.client.force_authenticate(self.user_with_restricted_write_perms)
        response = self.client.get(f"/api/polio/chronograms/template_tasks/{self.chronogram_template_task.pk}/")
        self.assertJSONResponse(response, 403)

        response = self.client.post("/api/polio/chronograms/template_tasks/", data={}, format="json")
        self.assertEqual(response.status_code, 403)

        response = self.client.patch(
            f"/api/polio/chronograms/template_tasks/{self.chronogram_template_task.pk}/", data={}, format="json"
        )
        self.assertEqual(response.status_code, 403)

        response = self.client.delete(f"/api/polio/chronograms/template_tasks/{self.chronogram_template_task.pk}/")
        self.assertEqual(response.status_code, 403)


@time_machine.travel(TODAY, tick=False)
class ChronogramViewSetTestCase(APITestCase):
    """
    Test ChronogramViewSet.
    """

    @classmethod
    def setUpTestData(cls):
        cls.data_source = m.DataSource.objects.create(name="Data Source")
        cls.source_version = m.SourceVersion.objects.create(data_source=cls.data_source, number=1)
        cls.account = m.Account.objects.create(name="Account", default_version=cls.source_version)
        cls.user = cls.create_user_with_profile(
            email="john@polio.org",
            username="john",
            first_name="John",
            last_name="Doe",
            account=cls.account,
            permissions=[iaso_permission._POLIO_CHRONOGRAM],
        )
        cls.user_with_restricted_write_perms = cls.create_user_with_profile(
            email="kevin@polio.org",
            username="kevin",
            first_name="Kevin",
            last_name="Walsh",
            account=cls.account,
            permissions=[iaso_permission._POLIO_CHRONOGRAM_RESTRICTED_WRITE],
        )

        cls.campaign = Campaign.objects.create(
            obr_name="Campaign OBR name", account=cls.account, country=m.OrgUnit.objects.create(name="Cameroon")
        )
        cls.polio_type = CampaignType.objects.get(name=CampaignType.POLIO)
        cls.campaign.campaign_types.add(cls.polio_type)

        cls.round_1 = Round.objects.create(number=1, campaign=cls.campaign, started_at=TODAY.date())
        cls.round_2 = Round.objects.create(number=2, campaign=cls.campaign, started_at=TODAY.date())

        cls.chronogram = Chronogram.objects.create(round=cls.round_2, created_by=cls.user)
        ChronogramTask.objects.create(
            period=Period.BEFORE,
            chronogram=cls.chronogram,
            description_en="Foo EN",
            description_fr="Foo FR",
            start_offset_in_days=0,
            user_in_charge="John Doe",
        )
        ChronogramTask.objects.create(
            period=Period.DURING,
            chronogram=cls.chronogram,
            description_en="Bar EN",
            description_fr="Bar FR",
            start_offset_in_days=0,
            user_in_charge="John Doe",
        )
        ChronogramTask.objects.create(
            period=Period.AFTER,
            chronogram=cls.chronogram,
            description_en="Baz EN",
            description_fr="BaZ FR",
            start_offset_in_days=0,
            user_in_charge="John Doe",
        )

    def test_get_without_auth(self):
        response = self.client.get(f"/api/polio/chronograms/{self.chronogram.pk}/")
        self.assertJSONResponse(response, 401)

    def test_get_without_perm(self):
        self.user.user_permissions.clear()
        self.client.force_authenticate(self.user)
        response = self.client.get(f"/api/polio/chronograms/{self.chronogram.pk}/")
        self.assertJSONResponse(response, 403)

    def test_get_ok(self):
        self.client.force_authenticate(self.user)

        with self.assertNumQueries(7):
            response = self.client.get(f"/api/polio/chronograms/{self.chronogram.pk}/")
            self.assertJSONResponse(response, 200)
            self.assertEqual(
                response.data,
                {
                    "id": self.chronogram.pk,
                    "campaign_obr_name": "Campaign OBR name",
                    "round_number": "2",
                    "round_start_date": "2024-06-27",
                    "is_on_time": True,
                    "num_task_delayed": 0,
                    "percentage_of_completion": {"BEFORE": 0, "DURING": 0, "AFTER": 0},
                },
            )

    def test_options_ok(self):
        self.client.force_authenticate(self.user)

        with self.assertNumQueries(4):
            response = self.client.options("/api/polio/chronograms/")
            self.assertJSONResponse(response, 200)

        self.assertIn("campaigns_filter_choices", response.data)
        self.assertEqual(
            response.data["campaigns_filter_choices"],
            [
                {
                    "value": str(self.campaign.id),
                    "display_name": self.campaign.obr_name,
                }
            ],
        )

    def test_get_all_fields_ok(self):
        self.client.force_authenticate(self.user)

        with self.assertNumQueries(7):
            response = self.client.get(f"/api/polio/chronograms/{self.chronogram.pk}/?fields=:all")
            self.assertJSONResponse(response, 200)
            self.assertEqual(len(response.data["tasks"]), 3)

    def test_create_ok(self):
        self.client.force_authenticate(self.user)
        data = {
            "round": self.round_1.pk,
        }
        response = self.client.post("/api/polio/chronograms/", data=data, format="json")
        self.assertEqual(response.status_code, 201)

        chronogram = Chronogram.objects.get(round=self.round_1)
        self.assertEqual(chronogram.created_by, self.user)
        self.assertEqual(chronogram.created_at, TODAY)
        self.assertEqual(chronogram.tasks.count(), 0)

    def test_update_should_be_forbidden(self):
        self.client.force_authenticate(self.user)
        response = self.client.put(f"/api/polio/chronograms/{self.chronogram.pk}/", data={}, format="json")
        self.assertEqual(response.status_code, 405)

    def test_soft_delete_ok(self):
        self.client.force_authenticate(self.user)
        response = self.client.delete(f"/api/polio/chronograms/{self.chronogram.pk}/", format="json")
        self.assertEqual(response.status_code, 204)

        self.chronogram.refresh_from_db()
        self.assertEqual(self.chronogram.deleted_at, TODAY)  # Soft deleted.

        tasks = self.chronogram.tasks.all()
        self.assertTrue(tasks.count() > 0)
        for task in tasks:
            self.assertEqual(task.deleted_at, TODAY)  # Soft deleted.

    def test_available_rounds_for_create(self):
        self.client.force_login(self.user)

        response = self.client.get("/api/polio/chronograms/available_rounds_for_create/")
        response_data = self.assertJSONResponse(response, 200)

        expected_data = {
            "countries": [{"value": self.campaign.country.id, "label": "Cameroon"}],
            "campaigns": [
                {"value": str(self.campaign.id), "label": "Campaign OBR name", "country_id": self.campaign.country.id}
            ],
            "rounds": [
                # Only round 1 should be available.
                {
                    "value": self.round_1.id,
                    "label": 1,
                    "campaign_id": str(self.campaign.id),
                    "target_population": None,
                },
            ],
        }
        self.assertEqual(response_data, expected_data)

        # Ensure test campaigns doesn't appear in the list.
        self.campaign.is_test = True
        self.campaign.save()
        response = self.client.get("/api/polio/chronograms/available_rounds_for_create/")
        response_data = self.assertJSONResponse(response, 200)
        expected_data = {
            "countries": [],
            "campaigns": [],
            "rounds": [],
        }
        self.assertEqual(response_data, expected_data)

    def test_for_user_with_restricted_access(self):
        """
        A user with restricted write permission should have access to safe methods only.
        """
        self.client.force_authenticate(self.user_with_restricted_write_perms)
        response = self.client.get(f"/api/polio/chronograms/{self.chronogram.pk}/")
        self.assertJSONResponse(response, 200)

        response = self.client.delete(f"/api/polio/chronograms/{self.chronogram.pk}/", format="json")
        self.assertEqual(response.status_code, 403)

        data = {"round": self.round_1.pk}
        response = self.client.post("/api/polio/chronograms/", data=data, format="json")
        self.assertEqual(response.status_code, 403)
