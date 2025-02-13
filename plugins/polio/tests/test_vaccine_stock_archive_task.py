from iaso.tests.tasks.task_api_test_case import TaskAPITestCase
import datetime

from django.contrib.auth.models import AnonymousUser
from django.utils.timezone import now

import hat.menupermissions.models as permissions
from iaso import models as m
from plugins.polio import models as pm


class TestVaccineStockArchive(TaskAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.data_source = m.DataSource.objects.create(name="Default source")
        cls.another_data_source = m.DataSource.objects.create(name="Another source")

        cls.now = now()

        cls.source_version_1 = m.SourceVersion.objects.create(data_source=cls.data_source, number=1)
        cls.another_source_version = m.SourceVersion.objects.create(data_source=cls.another_data_source, number=1)

        cls.account = m.Account.objects.create(name="polio", default_version=cls.source_version_1)

        cls.another_account = m.Account.objects.create(
            name="another_account", default_version=cls.another_source_version
        )

        cls.default_project = m.Project.objects.create(name="Default project", app_id="default", account=cls.account)
        cls.data_source.projects.set([cls.default_project])

        cls.another_project = m.Project.objects.create(
            name="Another project", app_id="another", account=cls.another_account
        )
        cls.another_data_source.projects.set([cls.another_project])

        cls.account_2 = m.Account.objects.create(name="second_account", default_version=cls.source_version_1)

        cls.anon = AnonymousUser()

        cls.user = cls.create_user_with_profile(
            username="user_2", account=cls.account, permissions=[permissions._POLIO_VACCINE_STOCK_MANAGEMENT_WRITE]
        )
        cls.user_no_perms = cls.create_user_with_profile(username="user_3", account=cls.account, permissions=[])

        cls.project = m.Project.objects.create(
            name="Polio",
            app_id="polio.projects",
            account=cls.account,
        )

        cls.project_2 = m.Project.objects.create(
            name="Project_2",
            app_id="pro.jects",
            account=cls.account_2,
        )

        cls.org_unit_type_country = m.OrgUnitType.objects.create(name="COUNTRY", category="COUNTRY")

        cls.org_unit_type_country.projects.set([cls.project, cls.project_2])
        cls.org_unit_type_country.save()

        # campaign RDC 1
        cls.org_unit_DRC = m.OrgUnit.objects.create(
            org_unit_type=cls.org_unit_type_country,
            version=cls.source_version_1,
            name="Democratic Republic of Congo",
            validation_status=m.OrgUnit.VALIDATION_VALID,
            source_ref="PvtAI4RUMkr",
        )

        cls.org_unit_CHAD = m.OrgUnit.objects.create(
            org_unit_type=cls.org_unit_type_country,
            version=cls.source_version_1,
            name="CHAD",
            validation_status=m.OrgUnit.VALIDATION_VALID,
            source_ref="PvtAI4RUMkr",
        )

        cls.campaign_rdc_1 = pm.Campaign.objects.create(
            obr_name="RDC_CAMPAIGN_1",
            country=cls.org_unit_DRC,
            account=cls.account,
            separate_scopes_per_round=False,
        )
        rdc_scope_group = m.Group.objects.create(name="campaign_rdc_1_scope", source_version=cls.source_version_1)
        rdc_scope_group.org_units.set([cls.org_unit_DRC])  # FIXME: we should actually have children org units
        cls.campaign_rdc_1_scope = pm.CampaignScope.objects.create(
            campaign=cls.campaign_rdc_1, vaccine=pm.VACCINES[0][0], group=rdc_scope_group
        )

        cls.campaign_rdc_1_round_1 = pm.Round.objects.create(
            campaign=cls.campaign_rdc_1,
            started_at=datetime.date(2021, 1, 1),
            ended_at=datetime.date(2021, 1, 10),
            number=1,
        )

        cls.campaign_rdc_1_round_2 = pm.Round.objects.create(
            campaign=cls.campaign_rdc_1,
            started_at=datetime.date(2021, 2, 1),
            ended_at=datetime.date(2021, 2, 10),
            number=2,
        )

        cls.campaign_rdc_1_round_3 = pm.Round.objects.create(
            campaign=cls.campaign_rdc_1,
            started_at=datetime.date(2021, 3, 1),
            ended_at=datetime.date(2021, 3, 10),
            number=3,
        )

        cls.vaccine_request_form_rdc_1 = pm.VaccineRequestForm.objects.create(
            campaign=cls.campaign_rdc_1,
            vaccine_type=pm.VACCINES[0][0],
            date_vrf_reception=cls.now - datetime.timedelta(days=30),
            date_vrf_signature=cls.now - datetime.timedelta(days=20),
            date_dg_approval=cls.now - datetime.timedelta(days=10),
            quantities_ordered_in_doses=500,
        )
        cls.vaccine_request_form_rdc_1.rounds.set([cls.campaign_rdc_1_round_1, cls.campaign_rdc_1_round_2])

        cls.vaccine_arrival_report_rdc_1 = pm.VaccineArrivalReport.objects.create(
            request_form=cls.vaccine_request_form_rdc_1,
            arrival_report_date=cls.campaign_rdc_1_round_1.started_at - datetime.timedelta(days=5),
            doses_received=400,
            doses_shipped=400,
            po_number="123",
            lot_numbers=["LOT123", "LOT456"],
            expiration_date=cls.now + datetime.timedelta(days=180),
            # the Model on save will implicitly set doses_per_vial to pm.DOSES_PER_VIAL[vaccine_type]
            # and calculated vials_received and vials_shipped
        )

        cls.vaccine_stock_rdc_mopv = pm.VaccineStock.objects.create(
            account=cls.account,
            country=cls.org_unit_DRC,
            vaccine=pm.VACCINES[0][0],
        )
        cls.outgoing_stock_movement_rdc_mopv_1 = pm.OutgoingStockMovement.objects.create(
            campaign=cls.campaign_rdc_1,
            vaccine_stock=cls.vaccine_stock_rdc_mopv,
            report_date=cls.campaign_rdc_1_round_1.started_at + datetime.timedelta(days=3),
            form_a_reception_date=cls.campaign_rdc_1_round_1.started_at + datetime.timedelta(days=3),
            usable_vials_used=10,  # 200 doses
            lot_numbers=["LOT123"],
            missing_vials=2,  # 40 doses
            comment="Hello world",
        )

        cls.incident_report_rdc_mopv_1 = pm.IncidentReport.objects.create(
            vaccine_stock=cls.vaccine_stock_rdc_mopv,
            stock_correction=pm.IncidentReport.StockCorrectionChoices.VVM_REACHED_DISCARD_POINT,
            date_of_incident_report=cls.campaign_rdc_1_round_1.started_at + datetime.timedelta(days=4),
            incident_report_received_by_rrt=cls.campaign_rdc_1_round_1.started_at + datetime.timedelta(days=4),
            unusable_vials=1,  # 1 vial/20 doses will be moved from usable to unusable
            usable_vials=0,
        )
        cls.incident_report_rdc_mopv_2 = pm.IncidentReport.objects.create(
            vaccine_stock=cls.vaccine_stock_rdc_mopv,
            stock_correction=pm.IncidentReport.StockCorrectionChoices.BROKEN,
            date_of_incident_report=cls.campaign_rdc_1_round_1.started_at + datetime.timedelta(days=5),
            incident_report_received_by_rrt=cls.campaign_rdc_1_round_1.started_at + datetime.timedelta(days=5),
            unusable_vials=0,
            usable_vials=1,  # 20 doses
        )
        cls.incident_report_rdc_mopv_3 = pm.IncidentReport.objects.create(
            vaccine_stock=cls.vaccine_stock_rdc_mopv,
            stock_correction=pm.IncidentReport.StockCorrectionChoices.PHYSICAL_INVENTORY_ADD,
            date_of_incident_report=cls.campaign_rdc_1_round_1.started_at + datetime.timedelta(days=6),
            incident_report_received_by_rrt=cls.campaign_rdc_1_round_1.started_at + datetime.timedelta(days=6),
            unusable_vials=0,
            usable_vials=16,  # 320 doses
        )
        cls.incident_report_rdc_mopv_4 = pm.IncidentReport.objects.create(
            vaccine_stock=cls.vaccine_stock_rdc_mopv,
            stock_correction=pm.IncidentReport.StockCorrectionChoices.PHYSICAL_INVENTORY_ADD,
            date_of_incident_report=cls.campaign_rdc_1_round_2.started_at + datetime.timedelta(days=6),
            incident_report_received_by_rrt=cls.campaign_rdc_1_round_2.started_at + datetime.timedelta(days=6),
            unusable_vials=0,
            usable_vials=10,  # 200 doses
        )
        cls.incident_report_rdc_mopv_5 = pm.IncidentReport.objects.create(
            vaccine_stock=cls.vaccine_stock_rdc_mopv,
            stock_correction=pm.IncidentReport.StockCorrectionChoices.PHYSICAL_INVENTORY_ADD,
            date_of_incident_report=cls.campaign_rdc_1_round_3.started_at + datetime.timedelta(days=6),
            incident_report_received_by_rrt=cls.campaign_rdc_1_round_3.started_at + datetime.timedelta(days=6),
            unusable_vials=0,
            usable_vials=10,  # 200 doses
        )
        # END campaign RDC 1

        # using chad for separate scopes per round
        cls.campaign_chad_1 = pm.Campaign.objects.create(
            obr_name="CHAD_CAMPAIGN_1",
            country=cls.org_unit_CHAD,
            account=cls.account,
            separate_scopes_per_round=True,
        )

        cls.campaign_chad_1_round_1 = pm.Round.objects.create(
            campaign=cls.campaign_chad_1,
            started_at=datetime.date(2021, 1, 1),
            ended_at=datetime.date(2021, 1, 10),
            number=1,
        )

        chad_round_1_scope_group = m.Group.objects.create(
            name="campaign_chad_1_scope", source_version=cls.source_version_1
        )
        chad_round_1_scope_group.org_units.set([cls.org_unit_CHAD])  # FIXME: we should actually have children org units
        cls.campaign_chad_1_round_1_scope = pm.RoundScope.objects.create(
            round=cls.campaign_chad_1_round_1, vaccine=pm.VACCINES[1][0], group=chad_round_1_scope_group
        )
        cls.campaign_chad_1_round_1.scopes.set([cls.campaign_chad_1_round_1_scope])

        cls.campaign_chad_1_round_2 = pm.Round.objects.create(
            campaign=cls.campaign_chad_1,
            started_at=datetime.date(2021, 2, 1),
            ended_at=datetime.date(2021, 2, 10),
            number=2,
        )

        chad_round_2_scope_group = m.Group.objects.create(
            name="campaign_chad_2_scope", source_version=cls.source_version_1
        )
        chad_round_2_scope_group.org_units.set([cls.org_unit_CHAD])  # FIXME: we should actually have children org units

        cls.campaign_chad_1_round_2_scope = pm.RoundScope.objects.create(
            round=cls.campaign_chad_1_round_2, vaccine=pm.VACCINES[0][0], group=chad_round_2_scope_group
        )

        cls.campaign_chad_1_round_2.scopes.set([cls.campaign_chad_1_round_2_scope])

        cls.campaign_chad_1_round_3 = pm.Round.objects.create(
            campaign=cls.campaign_chad_1,
            started_at=datetime.date(2021, 3, 1),
            ended_at=datetime.date(2021, 3, 10),
            number=3,
        )

        cls.vaccine_request_form_chad_1 = pm.VaccineRequestForm.objects.create(
            campaign=cls.campaign_chad_1,
            vaccine_type=pm.VACCINES[1][0],
            date_vrf_reception=cls.now - datetime.timedelta(days=30),
            date_vrf_signature=cls.now - datetime.timedelta(days=20),
            date_dg_approval=cls.now - datetime.timedelta(days=10),
            quantities_ordered_in_doses=500,
        )
        cls.vaccine_request_form_chad_2 = pm.VaccineRequestForm.objects.create(
            campaign=cls.campaign_chad_1,
            vaccine_type=pm.VACCINES[0][0],
            date_vrf_reception=cls.now - datetime.timedelta(days=30),
            date_vrf_signature=cls.now - datetime.timedelta(days=20),
            date_dg_approval=cls.now - datetime.timedelta(days=10),
            quantities_ordered_in_doses=500,
        )

        cls.vaccine_request_form_chad_1.rounds.set(
            [
                cls.campaign_chad_1_round_1,
                # cls.campaign_chad_1_round_2,
                # cls.campaign_chad_1_round_3,
            ]
        )
        cls.vaccine_request_form_chad_2.rounds.set(
            [
                # cls.campaign_chad_1_round_1,
                cls.campaign_chad_1_round_2,
                # cls.campaign_chad_1_round_3,
            ]
        )
        cls.vaccine_arrival_report_chad_1 = pm.VaccineArrivalReport.objects.create(
            request_form=cls.vaccine_request_form_chad_1,
            arrival_report_date=cls.campaign_chad_1_round_1.started_at - datetime.timedelta(days=5),
            doses_received=400,
            doses_shipped=400,  # 8 vials
            po_number="666",
            lot_numbers=["LOT789", "LOT45689"],
            expiration_date=cls.now + datetime.timedelta(days=180),
            # the Model on save will implicitly set doses_per_vial to pm.DOSES_PER_VIAL[vaccine_type]
            # and calculated vials_received and vials_shipped
        )

        cls.vaccine_stock_chad_nopv = pm.VaccineStock.objects.create(
            account=cls.account,
            country=cls.org_unit_CHAD,
            vaccine=pm.VACCINES[1][0],
        )
        cls.vaccine_stock_chad_mopv = pm.VaccineStock.objects.create(
            account=cls.account,
            country=cls.org_unit_CHAD,
            vaccine=pm.VACCINES[0][0],
        )
        cls.outgoing_stock_movement_chad_nopv_1 = pm.OutgoingStockMovement.objects.create(
            campaign=cls.campaign_rdc_1,
            vaccine_stock=cls.vaccine_stock_chad_nopv,
            report_date=cls.campaign_chad_1_round_1.started_at + datetime.timedelta(days=3),
            form_a_reception_date=cls.campaign_chad_1_round_1.started_at + datetime.timedelta(days=3),
            usable_vials_used=10,  # 500 doses
            lot_numbers=["LOT123"],
            missing_vials=2,  # 100 doses
            comment="Hello world",
        )

        cls.incident_report_chad_nopv_1 = pm.IncidentReport.objects.create(
            vaccine_stock=cls.vaccine_stock_chad_nopv,
            stock_correction=pm.IncidentReport.StockCorrectionChoices.VVM_REACHED_DISCARD_POINT,
            date_of_incident_report=cls.campaign_chad_1_round_1.started_at + datetime.timedelta(days=4),
            incident_report_received_by_rrt=cls.campaign_chad_1_round_1.started_at + datetime.timedelta(days=4),
            unusable_vials=1,  # 1 vial/50 doses will be moved from usable to unusable
            usable_vials=0,
        )
        cls.incident_report_chad_nopv_2 = pm.IncidentReport.objects.create(
            vaccine_stock=cls.vaccine_stock_chad_nopv,
            stock_correction=pm.IncidentReport.StockCorrectionChoices.BROKEN,
            date_of_incident_report=cls.campaign_chad_1_round_1.started_at + datetime.timedelta(days=5),
            incident_report_received_by_rrt=cls.campaign_chad_1_round_1.started_at + datetime.timedelta(days=5),
            unusable_vials=0,
            usable_vials=1,  # 50 doses
        )
        cls.incident_report_chad_nopv_3 = pm.IncidentReport.objects.create(
            vaccine_stock=cls.vaccine_stock_chad_nopv,
            stock_correction=pm.IncidentReport.StockCorrectionChoices.PHYSICAL_INVENTORY_ADD,
            date_of_incident_report=cls.campaign_chad_1_round_1.started_at + datetime.timedelta(days=6),
            incident_report_received_by_rrt=cls.campaign_chad_1_round_1.started_at + datetime.timedelta(days=6),
            unusable_vials=0,
            usable_vials=16,  # 800 doses
        )
        # should be ignored when computing round 1 values based on date
        cls.incident_report_rdc_chad_nopv_4 = pm.IncidentReport.objects.create(
            vaccine_stock=cls.vaccine_stock_chad_nopv,
            stock_correction=pm.IncidentReport.StockCorrectionChoices.PHYSICAL_INVENTORY_ADD,
            date_of_incident_report=cls.campaign_chad_1_round_2.started_at + datetime.timedelta(days=6),
            incident_report_received_by_rrt=cls.campaign_chad_1_round_2.started_at + datetime.timedelta(days=6),
            unusable_vials=0,
            usable_vials=10,  # 500 doses
        )
        cls.incident_report_rdc_chad_mopv = pm.IncidentReport.objects.create(
            vaccine_stock=cls.vaccine_stock_chad_mopv,
            stock_correction=pm.IncidentReport.StockCorrectionChoices.PHYSICAL_INVENTORY_ADD,
            date_of_incident_report=cls.campaign_chad_1_round_2.started_at + datetime.timedelta(days=6),
            incident_report_received_by_rrt=cls.campaign_chad_1_round_2.started_at + datetime.timedelta(days=6),
            unusable_vials=0,
            usable_vials=10,  # 100 doses
        )

    def test_anonymous_user_cannot_launch_task(self):
        self.client.force_authenticate(user=self.anon)
        response = self.client.post(
            "/api/tasks/create/archivevaccinestock/",
            {
                "campaign": self.campaign_rdc_1.obr_name,
                "vaccine": pm.VACCINES[0][0],  # mopv2, variables ato be renamed
                "date": "2021-01-26",  # with this date, round 1 should be archived
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_user_without_read_rights_cannot_launch_task(self):
        self.client.force_authenticate(user=self.user_no_perms)
        response = self.client.post(
            "/api/tasks/create/archivevaccinestock/",
            {
                "campaign": self.campaign_rdc_1.obr_name,
                "vaccine": pm.VACCINES[0][0],  # mopv2, variables ato be renamed
                "date": "2021-01-26",  # with this date, round 1 should be archived
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_task_archives_stock_for_round_ended_for_14_days(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/tasks/create/archivevaccinestock/",
            {
                "campaign": self.campaign_rdc_1.obr_name,
                "vaccine": pm.VACCINES[0][0],  # mopv2, variables ato be renamed
                "date": "2021-01-26",  # with this date, round 1 should be archived
            },
            format="json",
        )
        self.assertJSONResponse(response, 200)
        task = self.assertValidTaskAndInDB(response.json()["task"], status="QUEUED", name="archive_vaccine_stock")
        self.assertEqual(task.launcher, self.user)

        # Run the task
        self.runAndValidateTask(task, "SUCCESS")

        archived_round = pm.VaccineStockHistory.objects.filter(
            round_id=self.campaign_rdc_1_round_1, vaccine_stock__vaccine=pm.VACCINES[0][0]
        ).first()
        self.assertIsNotNone(archived_round)
        self.assertEqual(archived_round.vaccine_stock, self.vaccine_stock_rdc_mopv)
        self.assertEqual(archived_round.usable_doses_in, 440)
        self.assertEqual(archived_round.unusable_doses_in, 220)
        self.assertEqual(archived_round.usable_vials_in, 22)
        self.assertEqual(archived_round.unusable_vials_in, 11)

        # Launch second task with another date
        response = self.client.post(
            "/api/tasks/create/archivevaccinestock/",
            {
                "campaign": self.campaign_rdc_1.obr_name,
                "vaccine": pm.VACCINES[0][0],  # mopv2, variables ato be renamed
                "date": "2021-02-26",  # with this date,, round 2 should be archived
            },
            format="json",
        )
        self.assertJSONResponse(response, 200)
        task = self.assertValidTaskAndInDB(response.json()["task"], status="QUEUED", name="archive_vaccine_stock")
        self.assertEqual(task.launcher, self.user)

        # Run the task
        self.runAndValidateTask(task, "SUCCESS")
        # Checked that no archive has been added for round 1
        archived_round_1 = pm.VaccineStockHistory.objects.filter(
            round_id=self.campaign_rdc_1_round_1, vaccine_stock__vaccine=pm.VACCINES[0][0]
        )
        self.assertEqual(archived_round_1.count(), 1)

        archived_round_2 = pm.VaccineStockHistory.objects.filter(
            round_id=self.campaign_rdc_1_round_2, vaccine_stock__vaccine=pm.VACCINES[0][0]
        ).first()
        self.assertIsNotNone(archived_round_2)
        self.assertEqual(archived_round_2.vaccine_stock, self.vaccine_stock_rdc_mopv)
        self.assertEqual(archived_round_2.usable_doses_in, 640)
        self.assertEqual(archived_round_2.unusable_doses_in, 220)
        self.assertEqual(archived_round_2.usable_vials_in, 32)
        self.assertEqual(archived_round_2.unusable_vials_in, 11)

    # Also tests that round without vaccine in scope will not be archived
    def test_task_archives_stock_for_round_ended_for_14_days_separate_scopes_per_round(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/tasks/create/archivevaccinestock/",
            {
                "campaign": self.campaign_chad_1.obr_name,
                "vaccine": pm.VACCINES[1][0],  # mopv2
                "date": "2021-01-26",  # with this date, round 1 should be archived
            },
            format="json",
        )
        self.assertJSONResponse(response, 200)
        task = self.assertValidTaskAndInDB(response.json()["task"], status="QUEUED", name="archive_vaccine_stock")
        self.assertEqual(task.launcher, self.user)

        # Run the task
        self.runAndValidateTask(task, "SUCCESS")

        archived_round = pm.VaccineStockHistory.objects.filter(
            round_id=self.campaign_chad_1_round_1, vaccine_stock__vaccine=pm.VACCINES[1][0]
        ).first()
        self.assertIsNotNone(archived_round)
        self.assertEqual(archived_round.vaccine_stock, self.vaccine_stock_chad_nopv)
        self.assertEqual(archived_round.usable_doses_in, 500)
        self.assertEqual(archived_round.unusable_doses_in, 550)
        self.assertEqual(archived_round.usable_vials_in, 10)
        self.assertEqual(archived_round.unusable_vials_in, 11)

        # Launch second task with another date
        response = self.client.post(
            "/api/tasks/create/archivevaccinestock/",
            {
                "campaign": self.campaign_chad_1.obr_name,
                "vaccine": pm.VACCINES[1][0],  # mopv2
                "date": "2021-02-26",  # with this date,, round 2 should be archived
            },
            format="json",
        )
        self.assertJSONResponse(response, 200)
        task = self.assertValidTaskAndInDB(response.json()["task"], status="QUEUED", name="archive_vaccine_stock")
        self.assertEqual(task.launcher, self.user)

        # Run the task
        self.runAndValidateTask(task, "SUCCESS")
        # Checked that no archive has been added for round 1
        archived_round_1 = pm.VaccineStockHistory.objects.filter(
            round_id=self.campaign_chad_1_round_1, vaccine_stock__vaccine=pm.VACCINES[1][0]
        )
        self.assertEqual(archived_round_1.count(), 1)

        archived_round_2 = pm.VaccineStockHistory.objects.filter(
            round_id=self.campaign_chad_1_round_2, vaccine_stock__vaccine=pm.VACCINES[0][0]
        ).first()
        # Should be nothing for round 2 because it has no scope for this vaccine
        self.assertIsNone(archived_round_2)

    def test_for_campaign_without_selected_vaccine(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/tasks/create/archivevaccinestock/",
            {
                "campaign": self.campaign_rdc_1.obr_name,
                "vaccine": pm.VACCINES[1][0],  # wrong vaccine for campaign --> no archiving should be done
                "date": "2021-01-26",
            },
            format="json",
        )
        self.assertJSONResponse(response, 200)
        task = self.assertValidTaskAndInDB(response.json()["task"], status="QUEUED", name="archive_vaccine_stock")
        self.assertEqual(task.launcher, self.user)

        # Run the task
        self.runAndValidateTask(task, "SUCCESS")

        archived_round = pm.VaccineStockHistory.objects.filter(
            round_id=self.campaign_rdc_1_round_1, vaccine_stock__vaccine=pm.VACCINES[0][0]
        ).first()
        self.assertIsNone(archived_round)

    # All rounds for a campaign will have same data because there's no preexisting archive in this test
    def test_with_country_selected(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/tasks/create/archivevaccinestock/",
            {
                "country": self.org_unit_DRC.id,
            },  # should generate archive for all rounds since no date or vaccine were specified
            format="json",
        )
        self.assertJSONResponse(response, 200)
        task = self.assertValidTaskAndInDB(response.json()["task"], status="QUEUED", name="archive_vaccine_stock")
        self.assertEqual(task.launcher, self.user)

        # Run the task
        self.runAndValidateTask(task, "SUCCESS")

        archived_round_1 = pm.VaccineStockHistory.objects.filter(
            round_id=self.campaign_rdc_1_round_1, vaccine_stock__vaccine=pm.VACCINES[0][0]
        ).first()
        self.assertIsNotNone(archived_round_1)
        self.assertEqual(archived_round_1.vaccine_stock, self.vaccine_stock_rdc_mopv)
        self.assertEqual(archived_round_1.usable_doses_in, 840)
        self.assertEqual(archived_round_1.unusable_doses_in, 220)
        self.assertEqual(archived_round_1.usable_vials_in, 42)
        self.assertEqual(archived_round_1.unusable_vials_in, 11)

        archived_round_2 = pm.VaccineStockHistory.objects.filter(
            round_id=self.campaign_rdc_1_round_2, vaccine_stock__vaccine=pm.VACCINES[0][0]
        ).first()
        self.assertIsNotNone(archived_round_2)
        self.assertEqual(archived_round_2.vaccine_stock, self.vaccine_stock_rdc_mopv)
        self.assertEqual(archived_round_2.usable_doses_in, 840)
        self.assertEqual(archived_round_2.unusable_doses_in, 220)
        self.assertEqual(archived_round_2.usable_vials_in, 42)
        self.assertEqual(archived_round_2.unusable_vials_in, 11)

        archived_round_3 = pm.VaccineStockHistory.objects.filter(
            round_id=self.campaign_rdc_1_round_3, vaccine_stock__vaccine=pm.VACCINES[0][0]
        ).first()
        self.assertIsNotNone(archived_round_3)
        self.assertEqual(archived_round_3.vaccine_stock, self.vaccine_stock_rdc_mopv)
        self.assertEqual(archived_round_3.usable_doses_in, 840)
        self.assertEqual(archived_round_3.unusable_doses_in, 220)
        self.assertEqual(archived_round_3.usable_vials_in, 42)
        self.assertEqual(archived_round_3.unusable_vials_in, 11)

        # Check with chad that archives are created for each vaccine
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/tasks/create/archivevaccinestock/",
            {
                "country": self.org_unit_CHAD.id,
            },
            format="json",
        )
        self.assertJSONResponse(response, 200)
        task = self.assertValidTaskAndInDB(response.json()["task"], status="QUEUED", name="archive_vaccine_stock")
        self.assertEqual(task.launcher, self.user)

        # Run the task
        self.runAndValidateTask(task, "SUCCESS")

        archived_chad_round_1 = pm.VaccineStockHistory.objects.filter(
            round_id=self.campaign_chad_1_round_1, vaccine_stock__vaccine=pm.VACCINES[1][0]
        ).first()
        self.assertIsNotNone(archived_chad_round_1)
        self.assertEqual(archived_chad_round_1.vaccine_stock, self.vaccine_stock_chad_nopv)
        self.assertEqual(archived_chad_round_1.usable_doses_in, 1000)
        self.assertEqual(archived_chad_round_1.unusable_doses_in, 550)
        self.assertEqual(archived_chad_round_1.usable_vials_in, 20)
        self.assertEqual(archived_chad_round_1.unusable_vials_in, 11)

        archived_chad_round_2 = pm.VaccineStockHistory.objects.filter(
            round_id=self.campaign_chad_1_round_2, vaccine_stock__vaccine=pm.VACCINES[0][0]
        ).first()

        self.assertIsNotNone(archived_chad_round_2)
        self.assertEqual(archived_chad_round_2.vaccine_stock, self.vaccine_stock_chad_mopv)
        self.assertEqual(archived_chad_round_2.usable_doses_in, 200)
        self.assertEqual(archived_chad_round_2.unusable_doses_in, 0)
        self.assertEqual(archived_chad_round_2.usable_vials_in, 10)
        self.assertEqual(archived_chad_round_2.unusable_vials_in, 0)

    def test_with_no_params(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/tasks/create/archivevaccinestock/",
            format="json",
        )
        self.assertJSONResponse(response, 200)
        task = self.assertValidTaskAndInDB(response.json()["task"], status="QUEUED", name="archive_vaccine_stock")
        self.assertEqual(task.launcher, self.user)

        # Run the task
        self.runAndValidateTask(task, "SUCCESS")

        archived_drc_round_1 = pm.VaccineStockHistory.objects.filter(
            round_id=self.campaign_rdc_1_round_1, vaccine_stock__vaccine=pm.VACCINES[0][0]
        ).first()
        self.assertIsNotNone(archived_drc_round_1)
        self.assertEqual(archived_drc_round_1.vaccine_stock, self.vaccine_stock_rdc_mopv)
        self.assertEqual(archived_drc_round_1.usable_doses_in, 840)
        self.assertEqual(archived_drc_round_1.unusable_doses_in, 220)
        self.assertEqual(archived_drc_round_1.usable_vials_in, 42)
        self.assertEqual(archived_drc_round_1.unusable_vials_in, 11)

        archived_drc_round_2 = pm.VaccineStockHistory.objects.filter(
            round_id=self.campaign_rdc_1_round_2, vaccine_stock__vaccine=pm.VACCINES[0][0]
        ).first()
        self.assertIsNotNone(archived_drc_round_2)
        self.assertEqual(archived_drc_round_2.vaccine_stock, self.vaccine_stock_rdc_mopv)
        self.assertEqual(archived_drc_round_2.usable_doses_in, 840)
        self.assertEqual(archived_drc_round_2.unusable_doses_in, 220)
        self.assertEqual(archived_drc_round_2.usable_vials_in, 42)
        self.assertEqual(archived_drc_round_2.unusable_vials_in, 11)

        archived_drc_round_3 = pm.VaccineStockHistory.objects.filter(
            round_id=self.campaign_rdc_1_round_3, vaccine_stock__vaccine=pm.VACCINES[0][0]
        ).first()
        self.assertIsNotNone(archived_drc_round_3)
        self.assertEqual(archived_drc_round_3.vaccine_stock, self.vaccine_stock_rdc_mopv)
        self.assertEqual(archived_drc_round_3.usable_doses_in, 840)
        self.assertEqual(archived_drc_round_3.unusable_doses_in, 220)
        self.assertEqual(archived_drc_round_3.usable_vials_in, 42)
        self.assertEqual(archived_drc_round_3.unusable_vials_in, 11)

        archived_chad_round_1 = pm.VaccineStockHistory.objects.filter(
            round_id=self.campaign_chad_1_round_1, vaccine_stock__vaccine=pm.VACCINES[1][0]
        ).first()
        self.assertIsNotNone(archived_chad_round_1)
        self.assertEqual(archived_chad_round_1.vaccine_stock, self.vaccine_stock_chad_nopv)
        self.assertEqual(archived_chad_round_1.usable_doses_in, 1000)
        self.assertEqual(archived_chad_round_1.unusable_doses_in, 550)
        self.assertEqual(archived_chad_round_1.usable_vials_in, 20)
        self.assertEqual(archived_chad_round_1.unusable_vials_in, 11)

        archived_chad_round_2 = pm.VaccineStockHistory.objects.filter(
            round_id=self.campaign_chad_1_round_2, vaccine_stock__vaccine=pm.VACCINES[0][0]
        ).first()

        self.assertIsNotNone(archived_chad_round_2)
        self.assertEqual(archived_chad_round_2.vaccine_stock, self.vaccine_stock_chad_mopv)
        self.assertEqual(archived_chad_round_2.usable_doses_in, 200)
        self.assertEqual(archived_chad_round_2.unusable_doses_in, 0)
        self.assertEqual(archived_chad_round_2.usable_vials_in, 10)
        self.assertEqual(archived_chad_round_2.unusable_vials_in, 0)

    def test_archive_round_only_if_14_days_over(self):
        self.client.force_authenticate(user=self.user)
        # Less than 14 days after round 1 ended: no archive
        response = self.client.post(
            "/api/tasks/create/archivevaccinestock/",
            {
                "campaign": self.campaign_rdc_1.obr_name,
                "vaccine": pm.VACCINES[0][0],  # mopv2, variables ato be renamed
                "date": "2021-01-12",  # with this date, round 1 should be archived
            },
            format="json",
        )
        self.assertJSONResponse(response, 200)
        task = self.assertValidTaskAndInDB(response.json()["task"], status="QUEUED", name="archive_vaccine_stock")
        self.assertEqual(task.launcher, self.user)

        # Run the task
        self.runAndValidateTask(task, "SUCCESS")
        archived_round = pm.VaccineStockHistory.objects.filter(
            round_id=self.campaign_rdc_1_round_1, vaccine_stock__vaccine=pm.VACCINES[0][0]
        ).first()
        self.assertIsNone(archived_round)

        # More than 14 days --> archive
        response = self.client.post(
            "/api/tasks/create/archivevaccinestock/",
            {
                "campaign": self.campaign_rdc_1.obr_name,
                "vaccine": pm.VACCINES[0][0],  # mopv2, variables ato be renamed
                "date": "2021-01-26",  # with this date, round 1 should be archived
            },
            format="json",
        )
        self.assertJSONResponse(response, 200)
        task = self.assertValidTaskAndInDB(response.json()["task"], status="QUEUED", name="archive_vaccine_stock")
        self.assertEqual(task.launcher, self.user)

        # Run the task
        self.runAndValidateTask(task, "SUCCESS")
        archived_round = pm.VaccineStockHistory.objects.filter(
            round_id=self.campaign_rdc_1_round_1, vaccine_stock__vaccine=pm.VACCINES[0][0]
        ).first()
        self.assertIsNotNone(archived_round)
