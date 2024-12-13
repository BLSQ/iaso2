import csv
import datetime
import json
import io
from time import gmtime, strftime
from typing import List
from unittest import mock, skip
from unittest.mock import patch

import pandas as pd
from django.contrib.auth.models import User
from django.contrib.gis.geos import MultiPolygon, Point, Polygon
from django.core.cache import cache
from django.utils.timezone import now
from rest_framework import status
from rest_framework.test import APIClient

from iaso import models as m
from iaso.models import Account, Team
from iaso.models.json_config import Config
from iaso.test import APITestCase, TestCase
from plugins.polio.api.campaigns.campaigns import CampaignSerializer, CampaignViewSet
from plugins.polio.api.common import CACHE_VERSION
from plugins.polio.export_utils import format_date
from plugins.polio.models import CampaignScope, ReasonForDelay, Round, RoundScope
from plugins.polio.preparedness.calculator import get_preparedness_score
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
                "obr_name": "campaign_{}".format(n),
                "detection_status": "PENDING",
            }
            self.client.post("/api/polio/campaigns/", payload, format="json")

    def test_return_only_deleted_campaigns(self):
        self.create_multiple_campaigns(10)

        campaigns = Campaign.objects.all()

        for c in campaigns[:8]:
            self.client.delete("/api/polio/campaigns/{}/".format(c.id))

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
            self.client.delete("/api/polio/campaigns/{}/".format(c.id))

        response = self.client.get("/api/polio/campaigns/?campaigns=active", format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    def test_restore_deleted_campaign(self):
        self.create_multiple_campaigns(1)
        campaign = Campaign.objects.get()

        payload = {"id": campaign.id}

        if campaign.deleted_at is None:
            self.client.delete("/api/polio/campaigns/{}/".format(campaign.id))
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
            + round.vaccine_names()
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
            campaign.vaccines,
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


class CampaignCalculatorTestCase(TestCase):
    def setUp(self) -> None:
        with open("./plugins/polio/preparedness/test_data/example1.json") as json_data:
            self.preparedness_preview = json.load(json_data)

    def test_national_score(self):
        result = get_preparedness_score(self.preparedness_preview)
        self.assertEqual(result["national_score"], 93)

    def test_regional_score(self):
        result = get_preparedness_score(self.preparedness_preview)
        self.assertEqual(result["regional_score"], 68.4)

    def test_district_score(self):
        result = get_preparedness_score(self.preparedness_preview)
        self.assertAlmostEqual(result["district_score"], 56.25)


class LQASIMPolioTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.star_wars = star_wars = m.Account.objects.create(name="Star Wars")
        marvel = m.Account.objects.create(name="MCU")
        cls.project = m.Project.objects.create(
            name="Hydroponic gardens", app_id="stars.empire.agriculture.hydroponics", account=star_wars
        )
        sw_source = m.DataSource.objects.create(name="Evil Empire")
        sw_source.projects.add(cls.project)
        cls.sw_source = sw_source
        sw_version_1 = m.SourceVersion.objects.create(data_source=sw_source, number=1)
        sw_version_2 = m.SourceVersion.objects.create(data_source=sw_source, number=2)
        star_wars.default_version = sw_version_1
        star_wars.save()

        cls.jedi_squad = m.OrgUnitType.objects.create(name="Jedi Squad", short_name="Jds")

        cls.jedi_council = m.OrgUnitType.objects.create(name="Jedi Council", short_name="Cnc")
        cls.jedi_council.sub_unit_types.add(cls.jedi_squad)

        cls.mock_multipolygon = MultiPolygon(Polygon([[-1.3, 2.5], [-1.7, 2.8], [-1.1, 4.1], [-1.3, 2.5]]))
        cls.mock_point = Point(x=4, y=50, z=100)

        cls.elite_group = m.Group.objects.create(name="Elite councils")
        cls.unofficial_group = m.Group.objects.create(name="Unofficial Jedi councils")
        cls.another_group = m.Group.objects.create(name="Another group")

        cls.elite_group = m.Group.objects.create(name="Elite councils", source_version=sw_version_1)
        cls.unofficial_group = m.Group.objects.create(name="Unofficial Jedi councils")
        cls.another_group = m.Group.objects.create(name="Another group")

        cls.jedi_council_corruscant = m.OrgUnit.objects.create(
            org_unit_type=cls.jedi_council,
            version=sw_version_1,
            name="Corruscant Jedi Council",
            geom=cls.mock_multipolygon,
            simplified_geom=cls.mock_multipolygon,
            catchment=cls.mock_multipolygon,
            location=cls.mock_point,
            validation_status=m.OrgUnit.VALIDATION_VALID,
            source_ref="PvtAI4RUMkr",
        )
        cls.jedi_council_corruscant.groups.set([cls.elite_group])

        cls.jedi_council_endor = m.OrgUnit.objects.create(
            org_unit_type=cls.jedi_council,
            version=sw_version_1,
            name="Endor Jedi Council",
            geom=cls.mock_multipolygon,
            simplified_geom=cls.mock_multipolygon,
            catchment=cls.mock_multipolygon,
            location=cls.mock_point,
            validation_status=m.OrgUnit.VALIDATION_VALID,
        )
        cls.jedi_squad_endor = m.OrgUnit.objects.create(
            parent=cls.jedi_council_endor,
            org_unit_type=cls.jedi_squad,
            version=sw_version_1,
            name="Endor Jedi Squad 1",
            geom=cls.mock_multipolygon,
            simplified_geom=cls.mock_multipolygon,
            catchment=cls.mock_multipolygon,
            location=cls.mock_point,
            validation_status=m.OrgUnit.VALIDATION_VALID,
            source_ref="F9w3VW1cQmb",
        )
        cls.jedi_squad_endor = m.OrgUnit.objects.create(
            parent=cls.jedi_council_endor,
            org_unit_type=cls.jedi_squad,
            version=sw_version_1,
            name="Endor Jedi Squad 1",
            geom=cls.mock_multipolygon,
            simplified_geom=cls.mock_multipolygon,
            catchment=cls.mock_multipolygon,
            location=cls.mock_point,
            validation_status=m.OrgUnit.VALIDATION_VALID,
        )

        cls.jedi_council_brussels = m.OrgUnit.objects.create(
            org_unit_type=cls.jedi_council,
            version=sw_version_2,
            name="Brussels Jedi Council",
            geom=cls.mock_multipolygon,
            simplified_geom=cls.mock_multipolygon,
            catchment=cls.mock_multipolygon,
            location=cls.mock_point,
            validation_status=m.OrgUnit.VALIDATION_VALID,
        )

        cls.yoda = cls.create_user_with_profile(username="yoda", account=star_wars, permissions=["iaso_org_units"])
        cls.luke = cls.create_user_with_profile(
            username="luke", account=star_wars, permissions=["iaso_org_units"], org_units=[cls.jedi_council_endor]
        )
        cls.raccoon = cls.create_user_with_profile(username="raccoon", account=marvel, permissions=["iaso_org_units"])

        cls.form_1 = m.Form.objects.create(name="Hydroponics study", period_type=m.MONTH, single_per_period=True)

        cls.create_form_instance(
            form=cls.form_1, period="202001", org_unit=cls.jedi_council_corruscant, project=cls.project
        )

        cls.create_form_instance(
            form=cls.form_1, period="202001", org_unit=cls.jedi_council_corruscant, project=cls.project
        )

        cls.create_form_instance(
            form=cls.form_1, period="202003", org_unit=cls.jedi_council_corruscant, project=cls.project
        )

    def test_shapes_resp_is_cached(self):
        self.client.force_authenticate(self.yoda)

        response = self.client.get("/api/polio/campaigns/merged_shapes.geojson/")

        is_cached = True if cache.get("{}-geo_shapes".format(self.yoda.id), version=CACHE_VERSION) else False

        self.assertEqual(response.status_code, 200)
        self.assertEqual(is_cached, True)

    def test_general_status(self):
        c = Campaign.objects.create(account=self.star_wars)
        c.rounds.create(number=1, started_at=datetime.date(2021, 1, 1), ended_at=datetime.date(2021, 1, 2))
        c.rounds.create(number=2, started_at=datetime.date(2021, 3, 1), ended_at=datetime.date(2021, 3, 2))
        c.rounds.create(number=3, started_at=datetime.date(2021, 4, 1), ended_at=datetime.date(2021, 4, 20))

        with patch("django.utils.timezone.now", lambda: datetime.datetime(2020, 2, 2, 2, 2, 2)):
            d = CampaignSerializer(instance=c).data
            self.assertEqual(d["general_status"], "Preparing")
        with patch("django.utils.timezone.now", lambda: datetime.datetime(2021, 1, 1, 2, 2, 2)):
            d = CampaignSerializer(instance=c).data
            self.assertEqual(d["general_status"], "Round 1 started")
        with patch("django.utils.timezone.now", lambda: datetime.datetime(2021, 1, 3, 10, 2, 2)):
            d = CampaignSerializer(instance=c).data
            self.assertEqual(d["general_status"], "Round 1 ended")
        with patch("django.utils.timezone.now", lambda: datetime.datetime(2021, 4, 20, 10, 2, 2)):
            d = CampaignSerializer(instance=c).data
            self.assertEqual(d["general_status"], "Round 3 started")
