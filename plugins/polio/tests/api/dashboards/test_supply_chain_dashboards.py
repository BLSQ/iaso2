from datetime import date

from hat.menupermissions import models as permission
from iaso import models as m
from iaso.models.base import Account
from iaso.models.org_unit import OrgUnit, OrgUnitType
from iaso.test import APITestCase
from plugins.polio.models import (
    Campaign,
    DestructionReport,
    OutgoingStockMovement,
    RoundScope,
    VaccineArrivalReport,
    VaccinePreAlert,
    VaccineRequestForm,
    VaccineStock,
)
from plugins.polio.models.base import Round


class SupplyChainDashboardsAPITestCase(APITestCase):
    @classmethod
    def setUp(cls):
        cls.vrf_url = "/api/polio/dashboards/vaccine_request_forms/"
        cls.pre_alerts_url = "/api/polio/dashboards/pre_alerts/"
        cls.arrival_reports_url = "/api/polio/dashboards/arrival_reports/"
        cls.data_source = m.DataSource.objects.create(name="Default source")
        cls.source_version_1 = m.SourceVersion.objects.create(data_source=cls.data_source, number=1)
        cls.account = Account.objects.create(name="test account", default_version=cls.source_version_1)
        cls.other_account = Account.objects.create(name="other account")
        cls.authorized_user_read = cls.create_user_with_profile(
            username="authorized_read",
            account=cls.account,
            permissions=[
                permission._POLIO_VACCINE_SUPPLY_CHAIN_READ,
            ],
        )
        cls.unauthorized_user = cls.create_user_with_profile(
            username="unAuthorized", account=cls.account, permissions=[]
        )
        # We need the org unit type to be able to use campaign.country
        cls.country_type = OrgUnitType.objects.create(name="country", category="COUNTRY")
        cls.country = OrgUnit.objects.create(name="Outsiplou", org_unit_type=cls.country_type)
        cls.campaign = Campaign.objects.create(
            obr_name="Outsiplou-2024", account=cls.account, initial_org_unit=cls.country
        )
        cls.vaccine_type = "mOPV2"
        cls.other_campaign = Campaign.objects.create(obr_name="Not the expected result", account=cls.other_account)
        cls.vrf = VaccineRequestForm.objects.create(
            campaign=cls.campaign,
            date_vrf_signature=date.today(),
            date_vrf_reception=date.today(),
            date_dg_approval=date.today(),
            quantities_ordered_in_doses=1000,
            vaccine_type=cls.vaccine_type,
        )

        cls.round_1 = Round.objects.create(
            campaign=cls.campaign, number=1, started_at=date(2022, 1, 1), ended_at=date(2022, 1, 10)
        )
        cls.round_2 = Round.objects.create(
            campaign=cls.campaign, number=2, started_at=date(2022, 2, 1), ended_at=date(2022, 2, 10)
        )

        cls.vrf.rounds.set([cls.round_1, cls.round_2])
        cls.other_vrf = VaccineRequestForm.objects.create(
            campaign=cls.other_campaign,
            date_vrf_signature=date.today(),
            date_vrf_reception=date.today(),
            date_dg_approval=date.today(),
            quantities_ordered_in_doses=1000,
            vaccine_type=cls.vaccine_type,
        )
        cls.other_vrf.rounds.set([])
        cls.pre_alert = VaccinePreAlert.objects.create(request_form=cls.vrf, date_pre_alert_reception=date.today())
        cls.other_pre_alert = VaccinePreAlert.objects.create(
            request_form=cls.other_vrf, date_pre_alert_reception=date.today()
        )
        cls.arrival_report = VaccineArrivalReport.objects.create(
            request_form=cls.vrf, arrival_report_date=date.today(), doses_received=1000
        )
        cls.other_arrival_report = VaccineArrivalReport.objects.create(
            request_form=cls.other_vrf, arrival_report_date=date.today(), doses_received=1000
        )

        cls.vaccine_stock = VaccineStock.objects.create(
            country=cls.country, vaccine=cls.vaccine_type, account=cls.account
        )

        cls.form_a = OutgoingStockMovement.objects.create(
            campaign=cls.campaign,
            vaccine_stock=cls.vaccine_stock,
            report_date=date.today(),
            form_a_reception_date=date(2022, 2, 2),
            usable_vials_used=100,
            missing_vials=10,
        )

        cls.destruction_report = DestructionReport.objects.create(
            vaccine_stock=cls.vaccine_stock,
            rrt_destruction_report_reception_date=date(2022, 2, 9),
            destruction_report_date=date.today(),
            unusable_vials_destroyed=10,
            action="destroyed",
        )

    def test_user_has_permission_vrf(self):
        self.client.force_authenticate(self.unauthorized_user)
        response = self.client.get(self.vrf_url)
        self.assertJSONResponse(response, 403)

        self.client.force_authenticate(self.authorized_user_read)
        response = self.client.get(self.vrf_url)
        self.assertJSONResponse(response, 200)

    def test_user_has_permission_pre_alert(self):
        self.client.force_authenticate(self.unauthorized_user)
        response = self.client.get(self.pre_alerts_url)
        self.assertJSONResponse(response, 403)

        self.client.force_authenticate(self.authorized_user_read)
        response = self.client.get(self.pre_alerts_url)
        self.assertJSONResponse(response, 200)

    def test_user_has_permission_arrival_reports(self):
        self.client.force_authenticate(self.unauthorized_user)
        response = self.client.get(self.arrival_reports_url)
        self.assertJSONResponse(response, 403)

        self.client.force_authenticate(self.authorized_user_read)
        response = self.client.get(self.arrival_reports_url)
        self.assertJSONResponse(response, 200)
        # uncomment when write permission is effectively read-write
        # self.client.force_authenticate(self.authorized_user_write)
        # response = self.client.get(self.arrival_reports_url)
        # self.assertJSONResponse(response, 200)

    def test_vrf_filters_by_account(self):
        self.client.force_authenticate(self.authorized_user_read)
        response = self.client.get(self.vrf_url)
        jr = self.assertJSONResponse(response, 200)
        results = jr["results"]
        self.assertEqual(len(results), 1)
        vrf = results[0]
        self.assertEqual(vrf["obr_name"], self.campaign.obr_name)

    def test_vrf_new_fields(self):
        self.client.force_authenticate(self.authorized_user_read)

        response = self.client.get(self.vrf_url)

        jr = self.assertJSONResponse(response, 200)
        results = jr["results"]
        self.assertEqual(len(results), 1)
        vrf = results[0]
        self.assertEqual(vrf["obr_name"], self.campaign.obr_name)
        self.assertIn("stock_in_hand", vrf)
        self.assertIn("form_a_reception_date", vrf)
        self.assertIn("destruction_report_reception_date", vrf)

        # Check if the dates match with the created ArrivalReport and DestructionReport
        self.assertEqual(vrf["form_a_reception_date"], str(self.form_a.form_a_reception_date))
        self.assertEqual(
            vrf["destruction_report_reception_date"], str(self.destruction_report.rrt_destruction_report_reception_date)
        )

    def test_pre_alerts_filters_by_account(self):
        self.client.force_authenticate(self.authorized_user_read)
        response = self.client.get(self.pre_alerts_url)
        jr = self.assertJSONResponse(response, 200)
        results = jr["results"]
        self.assertEqual(len(results), 1)
        pre_alert = results[0]
        self.assertEqual(pre_alert["request_form"], self.vrf.pk)

    def test_arrival_reports_filters_by_account(self):
        self.client.force_authenticate(self.authorized_user_read)
        response = self.client.get(self.arrival_reports_url)
        jr = self.assertJSONResponse(response, 200)
        results = jr["results"]
        self.assertEqual(len(results), 1)
        arrival_report = results[0]
        self.assertEqual(arrival_report["request_form"], self.vrf.pk)

    def test_vrf_correct_dates_with_multiple_entries(self):
        self.client.force_authenticate(self.authorized_user_read)

        # Create another campaign and associated VaccineRequestForm, VaccinePreAlert, and VaccineArrivalReport
        new_campaign = Campaign.objects.create(
            obr_name="NewCampaign-2024",
            account=self.account,
            initial_org_unit=self.country,
            separate_scopes_per_round=True,
        )

        new_vrf = VaccineRequestForm.objects.create(
            campaign=new_campaign,
            date_vrf_signature=date.today(),
            date_vrf_reception=date.today(),
            date_dg_approval=date.today(),
            quantities_ordered_in_doses=2000,
            vaccine_type=self.vaccine_type,
        )
        new_vrf_round_1 = Round.objects.create(
            campaign=new_campaign, number=1, started_at=date(2023, 1, 1), ended_at=date(2023, 1, 10)
        )

        jedi_squad = m.OrgUnitType.objects.create(name="Jedi Squad", short_name="Jds")

        district_1 = OrgUnit.objects.create(
            id=5460, name="district 1", org_unit_type=jedi_squad, version=self.account.default_version
        )

        org_units_group_1 = m.Group.objects.create(name="group_1")
        org_units_group_1.org_units.add(district_1)
        org_units_group_1.save()

        rs = RoundScope.objects.create(vaccine=self.vaccine_type, round=new_vrf_round_1, group=org_units_group_1)

        new_vrf_round_2 = Round.objects.create(
            campaign=new_campaign, number=2, started_at=date(2024, 1, 1), ended_at=date(2024, 1, 10)
        )
        new_vrf.rounds.set([new_vrf_round_1, new_vrf_round_2])
        new_pre_alert = VaccinePreAlert.objects.create(request_form=new_vrf, date_pre_alert_reception=date.today())
        new_arrival_report = VaccineArrivalReport.objects.create(
            request_form=new_vrf, arrival_report_date=date.today(), doses_received=2000
        )

        # Should appear only in 2nd VRF
        new_forma = OutgoingStockMovement.objects.create(
            campaign=new_campaign,
            vaccine_stock=self.vaccine_stock,
            report_date=date.today(),
            form_a_reception_date=date(2024, 2, 1),
            usable_vials_used=60,
            missing_vials=6,
        )

        DestructionReport.objects.create(
            vaccine_stock=self.vaccine_stock,
            rrt_destruction_report_reception_date=date(2023, 3, 3),
            destruction_report_date=date(2023, 3, 3),
            unusable_vials_destroyed=6,
            action="destroyed",
        )

        last_dr = DestructionReport.objects.create(
            vaccine_stock=self.vaccine_stock,
            rrt_destruction_report_reception_date=date(2024, 2, 15),
            destruction_report_date=date(2024, 2, 15),
            unusable_vials_destroyed=6,
            action="destroyed",
        )

        response = self.client.get(self.vrf_url)
        jr = self.assertJSONResponse(response, 200)
        results = jr["results"]
        self.assertEqual(len(results), 2)
        vrf1 = results[0]

        # Check if the latest dates are returned
        self.assertEqual(vrf1["form_a_reception_date"], str(self.form_a.form_a_reception_date))
        self.assertEqual(
            vrf1["destruction_report_reception_date"],
            str(self.destruction_report.rrt_destruction_report_reception_date),
        )

        vrf2 = results[1]

        # Check if the latest dates are returned
        self.assertEqual(vrf2["form_a_reception_date"], str(new_forma.form_a_reception_date))
        self.assertEqual(vrf2["destruction_report_reception_date"], str(last_dr.rrt_destruction_report_reception_date))

    def test_default_pagination_is_added(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(f"{self.vrf_url}/")
        data = self.assertJSONResponse(response, 200)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["limit"], 20)
        response = self.client.get(f"{self.pre_alerts_url}/")
        data = self.assertJSONResponse(response, 200)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["limit"], 20)
        response = self.client.get(f"{self.arrival_reports_url}/")
        data = self.assertJSONResponse(response, 200)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["limit"], 20)

    def test_max_page_size_is_enforced(self):
        default_max_page_size = 1000  # default value from EtlPaginator
        self.client.force_authenticate(self.user)
        response = self.client.get(f"{self.vrf_url}?limit=2000&page=1")
        data = self.assertJSONResponse(response, 200)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["limit"], default_max_page_size)
        self.client.force_authenticate(self.user)
        response = self.client.get(f"{self.pre_alerts_url}?limit=2000&page=1")
        data = self.assertJSONResponse(response, 200)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["limit"], default_max_page_size)
        self.client.force_authenticate(self.user)
        response = self.client.get(f"{self.arrival_reports_url}?limit=2000&page=1")
        data = self.assertJSONResponse(response, 200)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["limit"], default_max_page_size)
