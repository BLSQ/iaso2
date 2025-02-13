import datetime
from typing import List
from unittest import mock, skip

import pandas as pd
from django.contrib.auth.models import User
from django.utils.timezone import now
from rest_framework import status
from rest_framework.test import APIClient

from iaso import models as m
from iaso.models import Account, Team
from iaso.test import APITestCase
from plugins.polio.export_utils import format_date
from plugins.polio.models import Campaign, CampaignType, ReasonForDelay, Round, RoundScope
from plugins.polio.preparedness.exceptions import InvalidFormatError
from plugins.polio.preparedness.spreadsheet_manager import *
from plugins.polio.tasks.weekly_email import send_notification_email


class PolioAPITestCase(APITestCase):
    data_source: m.DataSource
    now: datetime.datetime
    source_version_1: m.SourceVersion
    source_version_2: m.SourceVersion
    star_wars: m.Account
    jedi_squad: m.OrgUnitType
    yoda: User
    org_unit: m.OrgUnit
    child_org_unit: m.OrgUnit
    org_units: List[m.OrgUnit]
    luke: User
    account: m.Account

    @classmethod
    def setUpTestData(cls) -> None:
        cls.data_source = m.DataSource.objects.create(name="Default source")

        cls.now = now()

        cls.source_version_1 = m.SourceVersion.objects.create(data_source=cls.data_source, number=1)
        cls.source_version_2 = m.SourceVersion.objects.create(data_source=cls.data_source, number=2)
        cls.star_wars = m.Account.objects.create(name="Star Wars")
        cls.jedi_squad = m.OrgUnitType.objects.create(name="Jedi Squad", short_name="Jds")
        cls.account = Account.objects.create(name="Global Health Initiative", default_version=cls.source_version_1)
        cls.yoda = cls.create_user_with_profile(username="yoda", account=cls.account, permissions=["iaso_forms"])

        cls.org_unit = m.OrgUnit.objects.create(
            org_unit_type=m.OrgUnitType.objects.create(name="Jedi Council", short_name="Cnc"),
            version=cls.source_version_1,
            name="Jedi Council A",
            validation_status=m.OrgUnit.VALIDATION_VALID,
            source_ref="PvtAI4RUMkr",
        )

        cls.child_org_unit = m.OrgUnit.objects.create(
            org_unit_type=m.OrgUnitType.objects.create(name="Jedi Council", short_name="Cnc"),
            version=cls.source_version_1,
            name="Sub Jedi Council A",
            parent_id=cls.org_unit.id,
            validation_status=m.OrgUnit.VALIDATION_VALID,
            source_ref="PvtAI4RUMkr",
        )

        cls.org_units = [
            cls.org_unit,
            cls.child_org_unit,
            m.OrgUnit.objects.create(
                org_unit_type=m.OrgUnitType.objects.create(name="Jedi Council", short_name="Cnc"),
                version=cls.source_version_1,
                name="Jedi Council B",
                validation_status=m.OrgUnit.VALIDATION_VALID,
                source_ref="PvtAI4RUMkr",
            ),
        ]

        cls.luke = cls.create_user_with_profile(
            username="luke", account=cls.account, permissions=["iaso_forms"], org_units=[cls.child_org_unit]
        )
        cls.initial_data = ReasonForDelay.objects.create(
            account=cls.account, key_name="INITIAL_DATA", name_en="Initial data", name_fr="Données initiales"
        )
        cls.cat_ate_my_homework = ReasonForDelay.objects.create(
            account=cls.account,
            key_name="CAT_ATE_MY_HOMEWORK",
            name_en="The cat ate my homework",
            name_fr="Mon chat a mangé mon devoir",
        )

    def setUp(self) -> None:
        """Make sure we have a fresh client at the beginning of each test"""
        self.client = APIClient()
        self.client.force_authenticate(self.yoda)

    @mock.patch("plugins.polio.api.campaigns.campaigns.SpreadSheetImport")
    def test_preview_invalid_document(self, mock_SpreadSheetImport, *_):
        mock_SpreadSheetImport.create_for_url.return_value = mock.MagicMock()
        url = "https://docs.google.com/spreadsheets/d/1"
        error_message = "Error test_preview_invalid_document"
        mock_SpreadSheetImport.create_for_url.side_effect = InvalidFormatError(error_message)
        response = self.client.post("/api/polio/campaigns/preview_preparedness/", {"google_sheet_url": url})
        mock_SpreadSheetImport.create_for_url.assert_called_with(url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json().get("non_field_errors"), [error_message])

    def test_create_campaign(self):
        self.assertEqual(Campaign.objects.count(), 0)

        payload = {"obr_name": "obr_name", "detection_cstatus": "PENDING", "rounds": []}
        response = self.client.post("/api/polio/campaigns/", payload, format="json")
        self.assertJSONResponse(response, 201)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Campaign.objects.count(), 1)
        c = Campaign.objects.first()
        self.assertEqual(c.obr_name, "obr_name")
        self.assertEqual(c.account, self.account)

    def test_return_test_campaign_only(self):
        self.assertEqual(Campaign.objects.count(), 0)

        payload1 = {
            "account": self.account.pk,
            "obr_name": "obr_name",
            "detection_status": "PENDING",
            "is_test": True,
        }
        self.client.post("/api/polio/campaigns/", payload1, format="json")

        payload2 = {
            "account": self.account.pk,
            "obr_name": "obr_name_1",
            "detection_status": "PENDING",
            "is_test": False,
        }
        self.client.post("/api/polio/campaigns/", payload2, format="json")

        response = self.client.get("/api/polio/campaigns/?is_test=true")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    @skip("Skipping as long as PATCH is disabled for campaigns")
    def test_add_group_to_existing_campaign_without_group(self):
        """
        Ensure a group will be created when updating an existing campaign without a group
        """
        campaign = Campaign.objects.create(account=self.account)

        response = self.client.patch(
            f"/api/polio/campaigns/" + str(campaign.id) + "/",
            data={
                "obr_name": "campaign with org units",
                "scopes": [
                    {
                        "vaccine": "mOPV2",
                        "group": {
                            "org_units": list(map(lambda org_unit: org_unit.id, self.org_units)),
                        },
                    },
                ],
            },
            format="json",
        )
        self.assertJSONResponse(response, status.HTTP_200_OK)

        campaign.refresh_from_db()
        self.assertEqual(campaign.get_all_districts().count(), self.org_units.__len__())

    def test_can_create_and_update_campaign_with_orgunits_group(self):
        """
        Ensure we can create a new campaign object with org units group
        """

        self.client.force_authenticate(self.yoda)

        response = self.client.post(
            "/api/polio/campaigns/",
            data={
                "obr_name": "campaign with org units",
                "scopes": [
                    {
                        "vaccine": "mOPV2",
                        "group": {"org_units": [self.org_units[0].id]},
                    },
                ],
            },
            format="json",
        )

        self.assertJSONResponse(response, status.HTTP_201_CREATED)
        self.assertEqual(Campaign.objects.count(), 1)
        self.assertEqual(Campaign.objects.get().obr_name, "campaign with org units")
        self.assertEqual(Campaign.objects.get().scopes.first().group.org_units.count(), 1)

        response = self.client.put(
            f"/api/polio/campaigns/{str(Campaign.objects.get().id)}/",
            data={
                "account": self.account.pk,
                "obr_name": "campaign with org units",
                "scopes": [
                    {
                        "vaccine": "mOPV2",
                        "group": {
                            "org_units": list(map(lambda org_unit: org_unit.id, self.org_units)),
                        },
                    },
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(Campaign.objects.get().get_all_districts()), 3)

    def test_create_round_adds_history(self):
        """Check that adding a round adds a datelog with initial data"""
        self.client.force_authenticate(self.yoda)

        response = self.client.post(
            "/api/polio/campaigns/",
            data={
                "obr_name": "campaign with org units",
                "rounds": [{"number": 1, "started_at": "2023-03-21", "ended_at": "2023-04-01"}],
            },
            format="json",
        )
        jr = self.assertJSONResponse(response, 201)
        self.assertEqual(len(jr["rounds"]), 1)
        self.assertEqual(len(jr["rounds"][0]["datelogs"]), 1)
        self.assertEqual(jr["rounds"][0]["datelogs"][0]["reason_for_delay"], self.initial_data.key_name)

    def test_update_round_date_adds_history(self):
        """Updating round dates should add an entry in datelogs"""
        self.client.force_authenticate(self.yoda)

        response = self.client.post(
            "/api/polio/campaigns/",
            data={
                "obr_name": "campaign with org units",
                "rounds": [{"number": 1, "started_at": "2023-03-21", "ended_at": "2023-04-01"}],
            },
            format="json",
        )
        jr = self.assertJSONResponse(response, 201)
        campaign_id = jr["id"]
        datelogs = jr["rounds"][0]["datelogs"]
        new_datelog = {
            "previous_started_at": datelogs[0]["started_at"],
            "previous_ended_at": datelogs[0]["ended_at"],
            "started_at": datelogs[0]["started_at"],
            "ended_at": "2023-04-05",
            "reason_for_delay": self.cat_ate_my_homework.key_name,
        }
        datelogs.append(new_datelog)
        # Using PUT as it's how the UI proceeds
        response = self.client.put(
            f"/api/polio/campaigns/{campaign_id}/",
            data={
                "obr_name": "campaign with org units",
                "rounds": [
                    {
                        "number": 1,
                        "started_at": "2023-03-21",
                        "ended_at": "2023-04-05",
                        "datelogs": datelogs,
                    }
                ],
            },
            format="json",
        )
        jr = self.assertJSONResponse(response, 200)
        datelogs = jr["rounds"][0]["datelogs"]
        self.assertEqual(len(jr["rounds"][0]["datelogs"]), 2)
        self.assertEqual(jr["rounds"][0]["datelogs"][1]["reason_for_delay"], self.cat_ate_my_homework.key_name)
        self.assertEqual(jr["rounds"][0]["datelogs"][1]["ended_at"], "2023-04-05")
        self.assertEqual(jr["rounds"][0]["datelogs"][1]["previous_ended_at"], "2023-04-01")
        self.assertEqual(jr["rounds"][0]["datelogs"][1]["started_at"], "2023-03-21")
        self.assertEqual(jr["rounds"][0]["datelogs"][1]["previous_started_at"], "2023-03-21")

    def test_adding_a_new_round_should_generate_a_chronogram(self):
        """Adding a new round to a Polio campaign should generate a chronogram."""

        campaign = Campaign.objects.create(account=self.account, obr_name="obr_name")
        polio_type = CampaignType.objects.get(name=CampaignType.POLIO)
        campaign.campaign_types.add(polio_type)
        self.assertEqual(0, campaign.rounds.count())

        self.client.force_authenticate(self.yoda)

        # Add a round.
        response = self.client.put(
            f"/api/polio/campaigns/{campaign.id}/",
            data={
                "obr_name": campaign.obr_name,
                "rounds": [
                    {
                        "number": 1,
                        "started_at": now().date(),
                        "ended_at": (now() + datetime.timedelta(days=30)).date(),
                    }
                ],
            },
            format="json",
        )
        jr = self.assertJSONResponse(response, 200)
        self.assertEqual(1, campaign.rounds.count())

        round = campaign.rounds.first()
        self.assertEqual(round.chronograms.valid().count(), 1)
        self.assertIsNone(round.chronograms.valid().first().created_by)

    def test_can_only_see_campaigns_within_user_org_units_hierarchy(self):
        """
        Ensure a user can only see the campaigns for an org unit (or a descendent of that org unit) that was
        previously assigned to their profile
        """
        project = m.Project.objects.create(
            name="Hydroponic gardens", app_id="stars.empire.agriculture.hydroponics", account=self.star_wars
        )

        nopv2_team = Team.objects.create(name="NOPV2_VACCINE_TEAM_NAME", project=project, manager=self.yoda)

        nopv2_team.users.set([self.yoda.pk])

        payload = {
            "account": self.account.pk,
            "obr_name": "obr_name a",
            "detection_status": "PENDING",
            "initial_org_unit": self.org_unit.pk,
        }
        response = self.client.post("/api/polio/campaigns/", payload, format="json")
        self.assertEqual(response.status_code, 201)

        payload = {
            "account": self.account.pk,
            "obr_name": "obr_name b",
            "detection_status": "PENDING",
            "initial_org_unit": self.child_org_unit.pk,
        }
        self.client.force_authenticate(self.luke)
        response = self.client.post("/api/polio/campaigns/", payload, format="json")
        self.assertEqual(response.status_code, 201)

        response = self.client.get("/api/polio/campaigns/", format="json")

        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["initial_org_unit"], self.child_org_unit.pk)

    def test_polio_campaign_soft_delete(self):
        campaign = Campaign(obr_name="test_soft_delete", detection_status="PENDING", account=self.account)
        campaign.save()
        campaign.delete()
        last_campaign = Campaign.objects.last()
        self.assertEqual(last_campaign, campaign)

    def test_soft_deleted_campaign_weekly_mail(self):
        campaign_deleted = Campaign(
            obr_name="deleted_campaign",
            detection_status="PENDING",
            virus="ABC",
            country=self.org_unit,
            onset_at=now(),
            account=self.account,
        )

        campaign_active = Campaign(
            obr_name="active campaign",
            detection_status="PENDING",
            virus="ABC",
            country=self.org_unit,
            onset_at=now(),
            account=self.account,
        )

        country_user_grp = CountryUsersGroup(country=self.org_unit)
        country_user_grp.save()

        users = User.objects.all()
        country_user_grp.users.set(users)

        self.luke.email = "luketest@lukepoliotest.io"
        self.luke.save()

        campaign_deleted.save()
        campaign_deleted.delete()
        campaign_active.save()

        self.assertEqual(send_notification_email(campaign_deleted), False)
        self.assertEqual(send_notification_email(campaign_active), True)

    def test_weekly_mail_content(self):
        campaign_deleted = Campaign(
            obr_name="deleted_campaign",
            detection_status="PENDING",
            virus="ABC",
            country=self.org_unit,
            onset_at=now(),
            account=self.account,
        )

        campaign_active = Campaign(
            obr_name="active campaign",
            detection_status="PENDING",
            virus="ABC",
            country=self.org_unit,
            onset_at=now(),
            account=self.account,
        )

        country_user_grp = CountryUsersGroup(country=self.org_unit)
        country_user_grp.save()

        users = User.objects.all()
        country_user_grp.users.set(users)

        self.luke.email = "luketest@lukepoliotest.io"
        self.luke.save()

        campaign_deleted.save()
        campaign_deleted.delete()
        campaign_active.save()

        self.assertEqual(send_notification_email(campaign_deleted), False)
        self.assertEqual(send_notification_email(campaign_active), True)

    def test_weekly_mail_content_active_campaign(self):
        round = Round.objects.create(
            started_at=datetime.date(2022, 9, 12),
            number=1,
        )

        campaign_active = Campaign(
            obr_name="active campaign",
            detection_status="PENDING",
            virus="ABC",
            country=self.org_unit,
            onset_at=now().date(),
            account=self.account,
            cvdpv2_notified_at=datetime.date(2022, 9, 12),
        )

        round.campaign = campaign_active
        campaign_active.rounds.set([round])

        country_user_grp = CountryUsersGroup(country=self.org_unit)
        country_user_grp.save()

        users = User.objects.all()
        country_user_grp.users.set(users)

        self.luke.email = "luketest@lukepoliotest.io"
        self.luke.save()
        campaign_active.save()

        self.assertEqual(send_notification_email(campaign_active), True)

    def create_multiple_campaigns(self, count: int) -> None:
        for n in range(count):
            payload = {
                "account": self.account.pk,
                "obr_name": "campaign_{0}".format(n),
                "detection_status": "PENDING",
            }
            self.client.post("/api/polio/campaigns/", payload, format="json")

    def test_return_only_deleted_campaigns(self):
        self.create_multiple_campaigns(10)

        campaigns = Campaign.objects.all()

        for c in campaigns[:8]:
            self.client.delete("/api/polio/campaigns/{0}/".format(c.id))

        response = self.client.get("/api/polio/campaigns/?deletion_status=deleted", format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 8)

        # test that it return all
        response = self.client.get("/api/polio/campaigns/?deletion_status=all", format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 10)

        # per defaut it return undeleted
        response = self.client.get("/api/polio/campaigns/", format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)

        # filter on active
        response = self.client.get("/api/polio/campaigns/?deletion_status=active", format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)

    def test_return_only_active_campaigns(self):
        self.create_multiple_campaigns(3)

        campaigns = Campaign.objects.all()

        for c in campaigns[:2]:
            self.client.delete("/api/polio/campaigns/{0}/".format(c.id))

        response = self.client.get("/api/polio/campaigns/?campaigns=active", format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    def test_restore_deleted_campaign(self):
        self.create_multiple_campaigns(1)
        campaign = Campaign.objects.get()

        payload = {"id": campaign.id}

        if campaign.deleted_at is None:
            self.client.delete("/api/polio/campaigns/{0}/".format(campaign.id))
            self.client.patch("/api/polio/campaigns/restore_deleted_campaigns/", payload, format="json")

        restored_campaign = Campaign.objects.get(id=campaign.id)
        self.assertIsNone(restored_campaign.deleted_at)

    def test_create_calendar_xlsx_sheet(self):
        """
        It tests the whole export XLSX calendar feature when everything happens correctly:
            1. If the export succeed
            2. If it return the right header
            3. If the columns names are correct
            4. If the data in cells are correct:
                a. If there is on rounds in a cell
                b. If there are two rounds in a cell(it can be more than two rounds)
        """
        org_unit = OrgUnit.objects.create(
            id=5455,
            name="Country name",
            org_unit_type=self.jedi_squad,
            version=self.star_wars.default_version,
        )

        org_unit_2 = OrgUnit.objects.create(
            id=5456,
            name="Country name 2",
            org_unit_type=self.jedi_squad,
            version=self.star_wars.default_version,
        )

        c = Campaign.objects.create(country_id=org_unit.id, obr_name="orb campaign", account=self.account)

        c_round_1 = c.rounds.create(number=1, started_at=datetime.date(2022, 1, 1), ended_at=datetime.date(2022, 1, 2))
        c.rounds.create(number=2, started_at=datetime.date(2022, 3, 1), ended_at=datetime.date(2022, 3, 2))

        c2 = Campaign.objects.create(country_id=org_unit_2.id, obr_name="orb campaign 2", account=self.account)

        c2_round_1 = c2.rounds.create(
            number=1, started_at=datetime.date(2022, 1, 1), ended_at=datetime.date(2022, 1, 2)
        )
        c2_round_2 = c2.rounds.create(
            number=2, started_at=datetime.date(2022, 1, 4), ended_at=datetime.date(2022, 1, 7)
        )
        response = self.client.get("/api/polio/campaigns/create_calendar_xlsx_sheet/", {"currentDate": "2022-10-01"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get("Content-Disposition"), "attachment; filename=calendar_2022-10-01.xlsx")
        excel_data = pd.read_excel(response.content, engine="openpyxl", sheet_name="calendar_2022-10-01")

        excel_columns = excel_data.columns.ravel()
        self.assertEqual(excel_columns[0], "COUNTRY")
        self.assertEqual(excel_columns[3], "March")

        data_dict = excel_data.to_dict()
        self.assertEqual(data_dict["COUNTRY"][0], org_unit.name)
        self.assertEqual(data_dict["COUNTRY"][1], org_unit_2.name)
        self.assertEqual(data_dict["January"][0], self.format_date_to_test(c, c_round_1))
        self.assertEqual(data_dict["January"][1], self.format_date_to_test(c2, c2_round_1))
        self.assertEqual(data_dict["January"][2], self.format_date_to_test(c2, c2_round_2))

    def test_create_calendar_xlsx_sheet_campaign_without_country(self):
        """
        When a campaign was not linked to a country, export XLSX calendar triggered an error('NoneType' object has no attribute 'id'):
            - This test checks if the error does not occur even when a campaign is not linked to country
        """
        c = Campaign.objects.create(obr_name="orb campaign", account=self.account)
        c.rounds.create(number=1, started_at=datetime.date(2022, 1, 1), ended_at=datetime.date(2022, 1, 2))

        response = self.client.get("/api/polio/campaigns/create_calendar_xlsx_sheet/", {"currentDate": "2022-10-01"})
        self.assertEqual(response.status_code, 200)
        excel_data = pd.read_excel(response.content, engine="openpyxl", sheet_name="calendar_2022-10-01")

        data_dict = excel_data.to_dict()
        self.assertEqual(len(data_dict["COUNTRY"]), 0)

    def test_create_calendar_xlsx_sheet_round_with_no_end_date(self):
        """
        When a round had None in started_at or ended_at, it triggered an error('time data '' does not match format '%Y-%m-%d''):
            - This test checks if the error does not occur even when a round has None in started_at or ended_at
        """
        org_unit = OrgUnit.objects.create(
            id=5455,
            name="Country name",
            org_unit_type=self.jedi_squad,
            version=self.star_wars.default_version,
        )

        c = Campaign.objects.create(country_id=org_unit.id, obr_name="orb campaign", account=self.account)
        round = c.rounds.create(number=1, started_at=datetime.date(2022, 1, 1), ended_at=None)

        response = self.client.get("/api/polio/campaigns/create_calendar_xlsx_sheet/", {"currentDate": "2022-10-01"})
        self.assertEqual(response.status_code, 200)
        excel_data = pd.read_excel(response.content, engine="openpyxl", sheet_name="calendar_2022-10-01")

        data_dict = excel_data.to_dict()
        self.assertEqual(data_dict["January"][0], self.format_date_to_test(c, round))

    def test_create_calendar_xlsx_sheet_without_test_campaigns(self):
        """
        Test campaigns appeared in the XLSX, but they should not
            - This test is to make sure that no test campaign appear again in the XLSX calendar export
        """
        org_unit = OrgUnit.objects.create(
            id=5455,
            name="Country name",
            org_unit_type=self.jedi_squad,
            version=self.star_wars.default_version,
        )
        c = Campaign.objects.create(country_id=org_unit.id, obr_name="orb campaign", is_test=True, account=self.account)
        c.rounds.create(number=1, started_at=datetime.date(2022, 1, 1), ended_at=datetime.date(2022, 1, 2))

        response = self.client.get("/api/polio/campaigns/create_calendar_xlsx_sheet/", {"currentDate": "2022-10-01"})
        self.assertEqual(response.status_code, 200)
        excel_data = pd.read_excel(response.content, engine="openpyxl", sheet_name="calendar_2022-10-01")

        data_dict = excel_data.to_dict()
        self.assertEqual(len(data_dict["COUNTRY"]), 0)

    def test_create_calendar_xlsx_sheet_with_separate_scopes_per_round(self):
        """
        When a campaign is separeted into scopes per round:
            - This test checks if the xlsx file displays into separeted scopes per round
        """
        org_unit = OrgUnit.objects.create(
            id=5455,
            name="Country name",
            org_unit_type=self.jedi_squad,
            version=self.star_wars.default_version,
        )

        c = Campaign.objects.create(country_id=org_unit.id, obr_name="orb campaign", account=self.account)

        c_round_1 = Round.objects.create(
            number=1, started_at=datetime.date(2022, 1, 1), ended_at=datetime.date(2022, 1, 2)
        )
        c_round_2 = Round.objects.create(
            number=2, started_at=datetime.date(2022, 1, 3), ended_at=datetime.date(2022, 1, 4)
        )
        c.rounds.add(c_round_1)
        c.rounds.add(c_round_2)
        c.save()

        district_1 = OrgUnit.objects.create(
            id=5460,
            name="district 1",
            org_unit_type=self.jedi_squad,
            version=self.star_wars.default_version,
        )

        district_2 = OrgUnit.objects.create(
            id=5461,
            name="district 2",
            org_unit_type=self.jedi_squad,
            version=self.star_wars.default_version,
        )

        org_units_group_1 = m.Group.objects.create(name="group_1")
        org_units_group_1.org_units.add(district_1)
        org_units_group_1.save()

        org_units_group_2 = m.Group.objects.create(name="group_2")
        org_units_group_2.org_units.add(district_2)
        org_units_group_2.save()

        RoundScope.objects.create(vaccine="nOPV2", group=org_units_group_1, round=c_round_1)
        RoundScope.objects.create(vaccine="mOPV2", group=org_units_group_2, round=c_round_2)
        c.separate_scopes_per_round = True
        c.save()
        c.refresh_from_db()
        response = self.client.get("/api/polio/campaigns/create_calendar_xlsx_sheet/", {"currentDate": "2022-10-01"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get("Content-Disposition"), "attachment; filename=calendar_2022-10-01.xlsx")
        excel_data = pd.read_excel(response.content, engine="openpyxl", sheet_name="calendar_2022-10-01")

        excel_columns = excel_data.columns.ravel()
        self.assertEqual(excel_columns[0], "COUNTRY")
        self.assertEqual(excel_columns[3], "March")

        data_dict = excel_data.to_dict()
        self.assertEqual(data_dict["COUNTRY"][0], org_unit.name)
        self.assertEqual(data_dict["January"][0], self.format_date_to_test(c, c_round_1))
        self.assertEqual(data_dict["January"][1], self.format_date_to_test(c, c_round_2))

    @staticmethod
    def format_date_to_test(campaign, round):
        started_at = format_date(round.started_at.strftime("%Y-%m-%d")) if round.started_at is not None else ""
        ended_at = format_date(round.ended_at.strftime("%Y-%m-%d"), True) if round.ended_at is not None else ""
        return (
            campaign.obr_name
            + "\nRound "
            + str(round.number)
            + "\nDates: "
            + started_at
            + " - "
            + ended_at
            + "\n"
            + round.vaccine_names
            + "\n"
        )

    def test_handle_restore_active_campaign(self):
        self.create_multiple_campaigns(1)
        campaign = Campaign.objects.get()

        payload = {"id": campaign.id}

        response = self.client.patch("/api/polio/campaigns/restore_deleted_campaigns/", payload, format="json")

        self.assertEqual(response.status_code, 400)

    def test_handle_non_existant_campaign(self):
        payload = {"id": "bd656a6b-f67e-4a1e-95ee-1bef8f36239a"}
        response = self.client.patch("/api/polio/campaigns/restore_deleted_campaigns/", payload, format="json")
        self.assertEqual(response.status_code, 404)
