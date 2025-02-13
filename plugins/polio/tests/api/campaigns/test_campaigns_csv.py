import csv
import datetime
import io
from time import gmtime, strftime

from iaso import models as m
from iaso.models import Account
from iaso.test import APITestCase
from plugins.polio.api.campaigns.campaigns import CampaignViewSet
from plugins.polio.models import CampaignScope
from plugins.polio.preparedness.spreadsheet_manager import *


class PolioAPICampaignCsvTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.data_source = m.DataSource.objects.create(name="Default source")
        cls.source_version_1 = m.SourceVersion.objects.create(data_source=cls.data_source, number=1)
        cls.source_version_2 = m.SourceVersion.objects.create(data_source=cls.data_source, number=2)
        cls.star_wars = m.Account.objects.create(name="Star Wars")
        cls.jedi_squad = m.OrgUnitType.objects.create(name="Jedi Squad", short_name="Jds")
        cls.account = Account.objects.create(name="Global Health Initiative", default_version=cls.source_version_1)
        cls.yoda = cls.create_user_with_profile(username="yoda", account=cls.account, permissions=["iaso_forms"])

        cls.campaign_csv_columns = [x["title"] for x in CampaignViewSet.campaign_csv_columns()]

        def create_org_unit(id, name, type, version):
            return OrgUnit.objects.create(
                id=id,
                name=name,
                org_unit_type=type,
                version=version,
            )

        def create_campaign(id, obr_name, account):
            return Campaign.objects.create(
                country_id=id,
                obr_name=obr_name,
                account=account,
                onset_at=datetime.date(2022, 1, 1),
                cvdpv2_notified_at=datetime.date(2022, 1, 20),
                risk_assessment_first_draft_submitted_at=datetime.date(2022, 2, 1),
                risk_assessment_rrt_oprtt_approval_at=datetime.date(2022, 2, 25),
                submitted_to_rrt_at_WFEDITABLE=datetime.date(2022, 3, 1),
                approved_at_WFEDITABLE=datetime.date(2022, 3, 10),
                who_disbursed_to_co_at=datetime.date(2022, 3, 5),
                who_disbursed_to_moh_at=datetime.date(2022, 3, 8),
                unicef_disbursed_to_co_at=datetime.date(2022, 3, 4),
                unicef_disbursed_to_moh_at=datetime.date(2022, 3, 5),
                gpei_coordinator="Test coordinator",
            )

        cls.org_unit = create_org_unit(5453, "Country name", cls.jedi_squad, cls.star_wars.default_version)

        cls.org_unit_2 = create_org_unit(5454, "Country name 2", cls.jedi_squad, cls.star_wars.default_version)

        cls.district_1 = OrgUnit.objects.create(
            id=5460,
            name="district 1",
            org_unit_type=cls.jedi_squad,
            version=cls.star_wars.default_version,
        )

        cls.district_2 = OrgUnit.objects.create(
            id=5461,
            name="district 2",
            org_unit_type=cls.jedi_squad,
            version=cls.star_wars.default_version,
        )

        cls.org_units_group_1 = m.Group.objects.create(name="group_1")
        cls.org_units_group_1.org_units.add(cls.district_1)
        cls.org_units_group_1.save()

        cls.org_units_group_2 = m.Group.objects.create(name="group_2")
        cls.org_units_group_2.org_units.add(cls.district_2)
        cls.org_units_group_2.save()

        cls.c = create_campaign(cls.org_unit.id, "orb campaign", cls.account)
        cls.c2 = create_campaign(cls.org_unit_2.id, "orb campaign 2", cls.account)
        cls.c3 = create_campaign(None, "orb campaign 3", cls.account)
        cls.c_deleted = create_campaign(None, "orb campaign deleted", cls.account)
        cls.c_deleted.deleted_at = datetime.date(2022, 3, 5)
        cls.c_deleted.save()

    def row_data(self, campaign, round):
        return [
            campaign.country.name if campaign.country else "",
            campaign.obr_name,
            campaign.vaccines_extended,
            campaign.onset_at.strftime("%Y-%m-%d"),
            campaign.cvdpv2_notified_at.strftime("%Y-%m-%d"),
            str(round.number),
            round.started_at.strftime("%Y-%m-%d"),
            round.ended_at.strftime("%Y-%m-%d"),
            campaign.risk_assessment_first_draft_submitted_at.strftime("%Y-%m-%d"),
            campaign.risk_assessment_rrt_oprtt_approval_at.strftime("%Y-%m-%d"),
            campaign.submitted_to_rrt_at_WFEDITABLE.strftime("%Y-%m-%d"),
            campaign.approved_at_WFEDITABLE.strftime("%Y-%m-%d"),
            campaign.who_disbursed_to_co_at.strftime("%Y-%m-%d"),
            campaign.who_disbursed_to_moh_at.strftime("%Y-%m-%d"),
            campaign.unicef_disbursed_to_co_at.strftime("%Y-%m-%d"),
            campaign.unicef_disbursed_to_moh_at.strftime("%Y-%m-%d"),
            campaign.gpei_coordinator,
            str(round.target_population),
            str(round.doses_requested),
            str(round.cost),
            str(round.lqas_district_passing),
            str(round.lqas_district_failing),
            round.preparedness_spreadsheet_url,
            round.preparedness_sync_status,
        ]

    def test_csv_campaigns_export(self):
        """
        It tests the whole the csv campaigns file feature when everything happens correctly:
            1. If the export succeed
            2. If it return the right header
            3. If the columns names are correct
            4. If the data in cells are correct
        """

        c_round_1 = self.c.rounds.create(
            number=1,
            started_at=datetime.date(2022, 1, 1),
            ended_at=datetime.date(2022, 1, 2),
            target_population=1000,
            cost=10,
            lqas_district_passing=12,
            lqas_district_failing=2,
            preparedness_spreadsheet_url="https://docs.google.com/spreadsheets/d/test",
            preparedness_sync_status="FINISHED",
            doses_requested=0,
        )
        self.c.rounds.create(number=2, started_at=datetime.date(2022, 3, 1), ended_at=datetime.date(2022, 3, 2))

        CampaignScope.objects.create(vaccine="nOPV2", group=self.org_units_group_1, campaign=self.c)
        CampaignScope.objects.create(vaccine="mOPV2", group=self.org_units_group_2, campaign=self.c)

        self.c2.rounds.create(number=1, started_at=datetime.date(2022, 1, 1), ended_at=datetime.date(2022, 1, 2))
        self.c2.rounds.create(number=2, started_at=datetime.date(2022, 1, 4), ended_at=datetime.date(2022, 1, 7))

        response = self.client.get("/api/polio/campaigns/csv_campaigns_export/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get("Content-Disposition"),
            "attachment; filename=campaigns-rounds--" + strftime("%Y-%m-%d-%H-%M", gmtime()) + ".csv",
        )

        response_string = "\n".join(s.decode("U8") for s in response).replace("\r\n\n", "\r\n")
        reader = csv.reader(io.StringIO(response_string), delimiter=",")
        data = list(reader)
        self.assertEqual(len(data), 5)

        data_headers = data[0]
        self.assertEqual(
            data_headers,
            self.campaign_csv_columns,
        )
        first_data_row = data[1]
        row_data = self.row_data(self.c, c_round_1)

        self.assertEqual(
            first_data_row,
            row_data,
        )

    def test_csv_campaigns_export_filtered_data(self):
        """
        It tests the whole the csv campaigns file feature when everything happens correctly on filtered data:
            1. If the export succeed
            2. If it return the right header
            3. If the columns names are correct
            4. If the data in cells are correct
        """

        self.c.rounds.create(number=1, started_at=datetime.date(2022, 1, 1), ended_at=datetime.date(2022, 1, 2))
        self.c.rounds.create(number=2, started_at=datetime.date(2022, 3, 1), ended_at=datetime.date(2022, 3, 2))

        self.c2.is_test = True
        self.c2.save()

        c_round_2 = self.c2.rounds.create(
            number=1,
            started_at=datetime.date(2021, 12, 1),
            ended_at=datetime.date(2021, 12, 31),
            target_population=1500,
            cost=15,
            lqas_district_passing=16,
            lqas_district_failing=3,
            preparedness_spreadsheet_url="https://docs.google.com/spreadsheets/d/test2",
            preparedness_sync_status="FINISHED",
            doses_requested=0,
        )
        self.c2.rounds.create(number=2, started_at=datetime.date(2022, 1, 4), ended_at=datetime.date(2022, 1, 7))
        response = self.client.get(
            "/api/polio/campaigns/csv_campaigns_export/?campaign_category=test&show_test=true&enabled=true"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get("Content-Disposition"),
            "attachment; filename=campaigns-rounds--" + strftime("%Y-%m-%d-%H-%M", gmtime()) + ".csv",
        )

        response_string = "\n".join(s.decode("U8") for s in response).replace("\r\n\n", "\r\n")
        reader = csv.reader(io.StringIO(response_string), delimiter=",")
        data = list(reader)
        self.assertEqual(len(data), 3)
        data_headers = data[0]
        self.assertEqual(
            data_headers,
            self.campaign_csv_columns,
        )
        first_data_row = data[1]
        row_data = self.row_data(self.c2, c_round_2)
        self.assertEqual(
            first_data_row,
            row_data,
        )

    def test_csv_campaigns_export_campaing_with_no_country(self):
        """
        It tests the whole the csv campaigns file feature and check campaign with no country:
            1. If the export succeed
            2. If it return the right header
            3. If the columns names are correct
            4. If the data in cells are correct
            5. Display also campaigns not linked to country
        """

        self.c3.rounds.create(number=1, started_at=datetime.date(2022, 1, 1), ended_at=datetime.date(2022, 1, 2))
        self.c3.rounds.create(number=2, started_at=datetime.date(2022, 3, 1), ended_at=datetime.date(2022, 3, 2))

        c_round_2 = self.c3.rounds.create(
            number=1,
            started_at=datetime.date(2021, 12, 1),
            ended_at=datetime.date(2021, 12, 31),
            target_population=1500,
            cost=15,
            lqas_district_passing=16,
            lqas_district_failing=3,
            preparedness_spreadsheet_url="https://docs.google.com/spreadsheets/d/test3",
            preparedness_sync_status="FINISHED",
            doses_requested=0,
        )
        self.c3.rounds.create(number=2, started_at=datetime.date(2022, 1, 4), ended_at=datetime.date(2022, 1, 7))
        response = self.client.get("/api/polio/campaigns/csv_campaigns_export/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get("Content-Disposition"),
            "attachment; filename=campaigns-rounds--" + strftime("%Y-%m-%d-%H-%M", gmtime()) + ".csv",
        )

        response_string = "\n".join(s.decode("U8") for s in response).replace("\r\n\n", "\r\n")
        reader = csv.reader(io.StringIO(response_string), delimiter=",")
        data = list(reader)
        self.assertEqual(len(data), 5)
        data_headers = data[0]
        self.assertEqual(
            data_headers,
            self.campaign_csv_columns,
        )
        first_data_row = data[3]
        row_data = self.row_data(self.c3, c_round_2)
        self.assertEqual(
            first_data_row,
            row_data,
        )

    def test_csv_campaigns_export_no_deleted_and_deleted_campaigns(self):
        """
        It tests the csv export of no deleted and deleted compaigns:
            1. If the export succeed
            2. If it return the right header
            3. If the columns names are correct
            4. If the data in cells are correct
            5. First test it will display no deleted campaigns
            6. Second test it will display only deleted
        """

        self.c3.rounds.create(number=1, started_at=datetime.date(2022, 1, 1), ended_at=datetime.date(2022, 1, 2))
        self.c3.rounds.create(number=2, started_at=datetime.date(2022, 3, 1), ended_at=datetime.date(2022, 3, 2))
        self.c_deleted.rounds.create(number=1, started_at=datetime.date(2022, 1, 1), ended_at=datetime.date(2022, 1, 2))

        # It test the export with no deleted campaigns
        response_no_deleted = self.client.get("/api/polio/campaigns/csv_campaigns_export/")
        self.assertEqual(response_no_deleted.status_code, 200)
        self.assertEqual(
            response_no_deleted.get("Content-Disposition"),
            "attachment; filename=campaigns-rounds--" + strftime("%Y-%m-%d-%H-%M", gmtime()) + ".csv",
        )

        response_string = "\n".join(s.decode("U8") for s in response_no_deleted).replace("\r\n\n", "\r\n")
        reader = csv.reader(io.StringIO(response_string), delimiter=",")
        data = list(reader)
        self.assertEqual(len(data), 3)
        data_headers = data[0]
        self.assertEqual(
            data_headers,
            self.campaign_csv_columns,
        )

        # It test the export with only deleted campaigns
        response_deleted = self.client.get("/api/polio/campaigns/csv_campaigns_export/?deletion_status=deleted")
        self.assertEqual(response_deleted.status_code, 200)
        self.assertEqual(
            response_deleted.get("Content-Disposition"),
            "attachment; filename=campaigns-rounds--" + strftime("%Y-%m-%d-%H-%M", gmtime()) + ".csv",
        )

        response_string = "\n".join(s.decode("U8") for s in response_deleted).replace("\r\n\n", "\r\n")
        reader = csv.reader(io.StringIO(response_string), delimiter=",")
        data = list(reader)
        self.assertEqual(len(data), 2)
        data_headers = data[0]
        self.assertEqual(
            data_headers,
            self.campaign_csv_columns,
        )
