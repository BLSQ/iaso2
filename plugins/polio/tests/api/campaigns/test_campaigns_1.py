import datetime

from django.utils import timezone

from rest_framework.test import APIClient

from iaso import models as m
from iaso.models import Account
from iaso.test import APITestCase
from plugins.polio.models import CampaignType, Round
from plugins.polio.preparedness.spreadsheet_manager import *
from plugins.polio.tests.api.test import PolioTestCaseMixin


class PolioAPITestCase(APITestCase, PolioTestCaseMixin):
    data_source: m.DataSource
    source_version_1: m.SourceVersion
    org_unit: m.OrgUnit
    child_org_unit: m.OrgUnit

    @classmethod
    def setUpTestData(cls):
        cls.data_source = m.DataSource.objects.create(name="Default source")
        cls.now = timezone.now()
        cls.source_version_1 = m.SourceVersion.objects.create(data_source=cls.data_source, number=1)
        cls.account = polio_account = Account.objects.create(name="polio", default_version=cls.source_version_1)
        cls.user = cls.create_user_with_profile(username="yoda", account=polio_account, permissions=["iaso_forms"])

        cls.country_type = m.OrgUnitType.objects.create(name="COUNTRY", short_name="country")
        cls.district_type = m.OrgUnitType.objects.create(name="DISTRICT", short_name="district")

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

        cls.user_no_permission = cls.create_user_with_profile(
            username="luke", account=polio_account, permissions=["iaso_forms"], org_units=[cls.child_org_unit]
        )

    def setUp(self):
        """Make sure we have a fresh client at the beginning of each test"""
        self.client = APIClient()

    # TODO: consider moving all campaigns list tests to their own classes (for tighter/smaller test classes)
    def test_campaings_list_authenticated(self):
        """Basic tests for the campaigns list endpoint (while authenticated)

        Checks
        - the endpoint exists
        - the status code
        - important data fields get returned
        """
        self.client.force_authenticate(self.user)
        user_account = self.user.iaso_profile.account
        Campaign.objects.create(account=user_account, obr_name="obr_name", detection_status="PENDING")
        Campaign.objects.create(account=user_account, obr_name="obr_name2", detection_status="PENDING")

        response = self.client.get("/api/polio/campaigns/")
        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertEqual(len(json_response), 2)

        for campaign_data in json_response:
            # Both are part of the same account
            self.assertEqual(campaign_data["account"], user_account.pk)
            # TODO: test other fields here

    def test_campaings_list_authenticated_only_get_own_account(self):
        """Campaigns list endpoint: authenticated users only see results linked to their account"""
        self.client.force_authenticate(self.user)
        user_account = self.user.iaso_profile.account

        another_account = Account.objects.create(name="another_account")
        Campaign.objects.create(account=user_account, obr_name="obr_name", detection_status="PENDING")
        Campaign.objects.create(account=user_account, obr_name="obr_name2", detection_status="PENDING")
        Campaign.objects.create(account=another_account, obr_name="obr_name_other_account", detection_status="PENDING")

        json_response = self.client.get("/api/polio/campaigns/").json()
        self.assertEqual(len(json_response), 2)
        self.assertNotIn("obr_name_other_account", [c["obr_name"] for c in json_response])

    def test_campaigns_list_anonymous_can_choose_account(self):
        """Campaigns list endpoint: anonymous users only can use the account_id parameter to filter"""
        another_account = Account.objects.create(name="another_account")
        Campaign.objects.create(account=self.account, obr_name="obr_name", detection_status="PENDING")
        Campaign.objects.create(account=self.account, obr_name="obr_name2", detection_status="PENDING")
        Campaign.objects.create(account=another_account, obr_name="obr_name_other_account", detection_status="PENDING")

        json_response = self.client.get(f"/api/polio/campaigns/?account_id={another_account.pk}").json()
        self.assertEqual(len(json_response), 1)
        self.assertEqual(json_response[0]["obr_name"], "obr_name_other_account")

    def test_campaigns_list_anonymous_get_everything(self):
        """Campaigns list endpoint: if they don't use the account_id, anonymous users get everything"""
        another_account = Account.objects.create(name="another_account")
        Campaign.objects.create(account=self.account, obr_name="obr_name", detection_status="PENDING")
        Campaign.objects.create(account=self.account, obr_name="obr_name2", detection_status="PENDING")
        Campaign.objects.create(account=another_account, obr_name="obr_name_other_account", detection_status="PENDING")

        json_response = self.client.get("/api/polio/campaigns/").json()
        self.assertEqual(len(json_response), 3)

    def test_campaings_list_authenticated_account_id_ignored(self):
        """Campaigns list endpoint: authenticated users cannot make use of the account_id parameter

        Notes:
            - This is a bit counterintuitive since anonymous users can BUT this is because more data fields are shown
            to authenticated users
            - in practice, no error is thrown but the account_id parameter just gets ignored
        """
        self.client.force_authenticate(self.user)
        user_account = self.user.iaso_profile.account

        another_account = Account.objects.create(name="another_account")
        Campaign.objects.create(account=user_account, obr_name="obr_name", detection_status="PENDING")
        Campaign.objects.create(account=user_account, obr_name="obr_name2", detection_status="PENDING")
        Campaign.objects.create(account=another_account, obr_name="obr_name_other_account", detection_status="PENDING")

        json_response = self.client.get(f"/api/polio/campaigns/?account_id={another_account.pk}").json()
        self.assertEqual(len(json_response), 2)
        self.assertNotIn("obr_name_other_account", [c["obr_name"] for c in json_response])

    def test_campaigns_list_anonymous(self):
        """Basic tests for the campaigns list endpoint (anonymous)

        Checks
        - the endpoint exists
        - the status code
        - important data fields get returned
        """
        Campaign.objects.create(account=self.account, obr_name="obr_name", detection_status="PENDING")
        Campaign.objects.create(account=self.account, obr_name="obr_name2", detection_status="PENDING")

        response = self.client.get("/api/polio/campaigns/")
        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertEqual(len(json_response), 2)

        for campaign_data in json_response:
            # Both are part of the same account
            self.assertEqual(campaign_data["account"], self.account.pk)
            # TODO: test other fields (all that's needed for anonymous access) here

    def test_create_campaign_account_not_mandatory(self):
        """Campaigns ca be created without an account"""
        self.client.force_authenticate(self.user)
        payload = {
            "obr_name": "obr_name",
            "detection_status": "PENDING",
            "rounds": [
                {
                    "number": 0,
                    "started_at": "2021-02-01",
                    "ended_at": "2021-02-20",
                }
            ],
        }
        response = self.client.post("/api/polio/campaigns/", payload, format="json")
        self.assertEqual(Campaign.objects.count(), 1)
        self.assertEqual(response.status_code, 201)

    def test_cannot_create_campaigns_if_not_authenticated(self):
        payload = {
            "account": self.account.pk,
            "obr_name": "obr_name",
            "detection_status": "PENDING",
            "rounds": [
                {
                    "number": 0,
                    "started_at": "2021-02-01",
                    "ended_at": "2021-02-20",
                }
            ],
        }
        response = self.client.post("/api/polio/campaigns/", payload, format="json")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(Campaign.objects.count(), 0)

    def test_create_campaign(self):
        self.client.force_authenticate(self.user)
        self.assertEqual(Campaign.objects.count(), 0)

        started_at = self.now.strftime("%Y-%m-%d")
        ended_at = (self.now + datetime.timedelta(days=20)).strftime("%Y-%m-%d")
        payload = {
            "account": self.account.pk,
            "obr_name": "obr_name",
            "detection_status": "PENDING",
            "rounds": [
                {
                    "number": 0,
                    "started_at": started_at,
                    "ended_at": ended_at,
                }
            ],
        }
        response = self.client.post("/api/polio/campaigns/", payload, format="json")

        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(Campaign.objects.count(), 1)
        c = Campaign.objects.first()
        self.assertEqual(c.obr_name, "obr_name")
        rounds = c.rounds.all()
        self.assertEqual(1, rounds.count())
        round_zero = rounds.first()
        self.assertEqual(round_zero.number, 0)

        # A chronogram should've been automatically created for the new round.
        self.assertEqual(round_zero.chronograms.valid().count(), 1)
        chronogram = round_zero.chronograms.valid().first()
        self.assertIsNone(chronogram.created_by)

        response = self.client.get(f"/api/polio/campaigns/{c.id}/", payload, format="json")

        r = self.assertJSONResponse(response, 200)
        self.assertEqual(len(r["rounds"]), 1)

    def test_create_campaign_with_round_one(self):
        self.client.force_authenticate(self.user)
        self.assertEqual(Campaign.objects.count(), 0)

        started_at = self.now.strftime("%Y-%m-%d")
        ended_at = (self.now + datetime.timedelta(days=20)).strftime("%Y-%m-%d")
        payload = {
            "account": self.account.pk,
            "obr_name": "obr_name",
            "detection_status": "PENDING",
            "rounds": [
                {
                    "number": 1,
                    "started_at": started_at,
                    "ended_at": ended_at,
                }
            ],
        }
        response = self.client.post("/api/polio/campaigns/", payload, format="json")

        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(Campaign.objects.count(), 1)
        c = Campaign.objects.first()
        self.assertEqual(c.obr_name, "obr_name")
        rounds = c.rounds.all()
        self.assertEqual(1, rounds.count())
        round_zero = rounds.first()
        self.assertEqual(round_zero.number, 1)

        # A chronogram should've been automatically created for the new round.
        self.assertEqual(round_zero.chronograms.valid().count(), 1)
        chronogram = round_zero.chronograms.valid().first()
        self.assertIsNone(chronogram.created_by)

        response = self.client.get(f"/api/polio/campaigns/{c.id}/", payload, format="json")

        r = self.assertJSONResponse(response, 200)
        self.assertEqual(len(r["rounds"]), 1)
        self.assertEqual(r["rounds"][0]["started_at"], started_at)

    def test_create_campaign_with_round_one_and_two(self):
        self.client.force_authenticate(self.user)
        self.assertEqual(Campaign.objects.count(), 0)

        started_at_round_1 = self.now.strftime("%Y-%m-%d")
        ended_at_round_1 = (self.now + datetime.timedelta(days=20)).strftime("%Y-%m-%d")
        started_at_round_2 = (self.now + datetime.timedelta(days=60)).strftime("%Y-%m-%d")
        ended_at_round_2 = (self.now + datetime.timedelta(days=80)).strftime("%Y-%m-%d")
        payload = {
            "account": self.account.pk,
            "obr_name": "obr_name",
            "detection_status": "PENDING",
            "rounds": [
                {
                    "number": 1,
                    "started_at": started_at_round_1,
                    "ended_at": ended_at_round_1,
                },
                {
                    "number": 2,
                    "started_at": started_at_round_2,
                    "ended_at": ended_at_round_2,
                },
            ],
        }
        response = self.client.post("/api/polio/campaigns/", payload, format="json")

        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(Campaign.objects.count(), 1)
        c = Campaign.objects.first()
        self.assertEqual(c.obr_name, "obr_name")
        rounds = c.rounds.all().order_by("number")
        self.assertEqual(2, rounds.count())
        self.assertQuerySetEqual(rounds, [1, 2], lambda r: r.number)

        # A chronogram should've been automatically created for each new round.
        round_1 = c.rounds.first()
        self.assertEqual(round_1.chronograms.valid().count(), 1)
        self.assertIsNone(round_1.chronograms.valid().first().created_by)
        round_2 = c.rounds.last()
        self.assertEqual(round_2.chronograms.valid().count(), 1)
        self.assertIsNone(round_2.chronograms.valid().first().created_by)

        response = self.client.get(f"/api/polio/campaigns/{c.id}/", format="json")
        r = self.assertJSONResponse(response, 200)
        self.assertEqual(len(r["rounds"]), 2)
        self.assertEqual(r["rounds"][0]["started_at"], started_at_round_1)
        self.assertEqual(r["rounds"][1]["started_at"], started_at_round_2)

    def test_create_campaign_with_scopes(self):
        self.client.force_authenticate(self.user)
        self.assertEqual(Campaign.objects.count(), 0)

        started_at_round_1 = self.now.strftime("%Y-%m-%d")
        ended_at_round_1 = (self.now + datetime.timedelta(days=20)).strftime("%Y-%m-%d")
        started_at_round_2 = (self.now + datetime.timedelta(days=60)).strftime("%Y-%m-%d")
        ended_at_round_2 = (self.now + datetime.timedelta(days=80)).strftime("%Y-%m-%d")
        payload = {
            "account": self.account.pk,
            "obr_name": "obr_name",
            "separate_scopes_per_round": False,
            "scopes": [
                {"vaccine": "bOPV", "group": {"org_units": [self.org_unit.id]}},
                {"vaccine": "mOPV2", "group": {"org_units": [self.child_org_unit.id]}},
            ],
            "rounds": [
                {
                    "number": 1,
                    "started_at": started_at_round_1,
                    "ended_at": ended_at_round_1,
                },
                {
                    "number": 2,
                    "started_at": started_at_round_2,
                    "ended_at": ended_at_round_2,
                },
            ],
        }

        response = self.client.post("/api/polio/campaigns/", payload, format="json")

        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(Campaign.objects.count(), 1)
        c = Campaign.objects.first()
        self.assertEqual(c.obr_name, "obr_name")
        rounds = c.rounds.all().order_by("number")
        self.assertEqual(2, rounds.count())
        self.assertQuerySetEqual(rounds, [1, 2], lambda r: r.number)
        self.assertQuerySetEqual(c.scopes.get(vaccine="bOPV").group.org_units.all(), [self.org_unit])
        self.assertEqual(c.scopes.get(vaccine="bOPV").group.source_version, self.org_unit.version)
        self.assertQuerySetEqual(c.scopes.get(vaccine="mOPV2").group.org_units.all(), [self.child_org_unit])
        # check via the api
        response = self.client.get(f"/api/polio/campaigns/{c.id}/", format="json")
        r = self.assertJSONResponse(response, 200)
        self.assertEqual(len(r["rounds"]), 2)
        self.assertEqual(r["rounds"][0]["started_at"], started_at_round_1)
        self.assertEqual(r["rounds"][0]["districts_count_calculated"], 2)
        self.assertEqual(r["rounds"][1]["started_at"], started_at_round_2)
        self.assertEqual(r["rounds"][1]["districts_count_calculated"], 2)

        # A chronogram should've been automatically created for each new round.
        round_1 = c.rounds.get(id=r["rounds"][0]["id"])
        self.assertEqual(round_1.chronograms.valid().count(), 1)
        self.assertIsNone(round_1.chronograms.valid().first().created_by)
        round_2 = c.rounds.get(id=r["rounds"][1]["id"])
        self.assertEqual(round_2.chronograms.valid().count(), 1)
        self.assertIsNone(round_2.chronograms.valid().first().created_by)

        scope_bOPV = c.scopes.get(vaccine="bOPV")
        scope_mOPV2 = c.scopes.get(vaccine="mOPV2")
        self.assertEqual(
            r["scopes"],
            [
                {
                    "vaccine": "bOPV",
                    "group": {
                        "name": scope_bOPV.group.name,
                        "id": scope_bOPV.group.id,
                        "org_units": [o.id for o in scope_bOPV.group.org_units.all()],
                    },
                },
                {
                    "vaccine": "mOPV2",
                    "group": {
                        "name": scope_mOPV2.group.name,
                        "id": scope_mOPV2.group.id,
                        "org_units": [o.id for o in scope_mOPV2.group.org_units.all()],
                    },
                },
            ],
        )

    def test_create_campaign_with_round_scopes(self):
        self.client.force_authenticate(self.user)
        self.assertEqual(Campaign.objects.count(), 0)

        started_at_round_1 = self.now.strftime("%Y-%m-%d")
        ended_at_round_1 = (self.now + datetime.timedelta(days=20)).strftime("%Y-%m-%d")
        started_at_round_2 = (self.now + datetime.timedelta(days=60)).strftime("%Y-%m-%d")
        ended_at_round_2 = (self.now + datetime.timedelta(days=80)).strftime("%Y-%m-%d")
        payload = {
            "account": self.account.pk,
            "obr_name": "obr_name",
            "detection_status": "PENDING",
            "separate_scopes_per_round": True,
            "rounds": [
                {
                    "number": 1,
                    "started_at": started_at_round_1,
                    "ended_at": ended_at_round_1,
                    "scopes": [
                        {"vaccine": "bOPV", "group": {"org_units": [self.org_unit.id]}},
                        {"vaccine": "mOPV2", "group": {"org_units": [self.child_org_unit.id]}},
                    ],
                },
                {
                    "number": 2,
                    "started_at": started_at_round_2,
                    "ended_at": ended_at_round_2,
                },
            ],
        }

        response = self.client.post("/api/polio/campaigns/", payload, format="json")

        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(Campaign.objects.count(), 1)
        c = Campaign.objects.first()
        self.assertEqual(c.obr_name, "obr_name")
        rounds = c.rounds.all().order_by("number")
        self.assertEqual(2, rounds.count())
        self.assertQuerySetEqual(rounds, [1, 2], lambda r: r.number)
        first_round = c.rounds.filter(number=1).first()
        self.assertQuerySetEqual(first_round.scopes.get(vaccine="bOPV").group.org_units.all(), [self.org_unit])
        self.assertQuerySetEqual(first_round.scopes.get(vaccine="mOPV2").group.org_units.all(), [self.child_org_unit])
        response = self.client.get(f"/api/polio/campaigns/{c.id}/", format="json")
        r = self.assertJSONResponse(response, 200)
        self.assertEqual(len(r["rounds"]), 2)
        self.assertEqual(r["rounds"][0]["started_at"], started_at_round_1)
        self.assertEqual(r["rounds"][0]["districts_count_calculated"], 2)
        self.assertEqual(r["rounds"][1]["started_at"], started_at_round_2)
        self.assertEqual(r["rounds"][1]["districts_count_calculated"], 0)

        # A chronogram should've been automatically created for each new round.
        round_1 = c.rounds.get(id=r["rounds"][0]["id"])
        self.assertEqual(round_1.chronograms.valid().count(), 1)
        self.assertIsNone(round_1.chronograms.valid().first().created_by)
        round_2 = c.rounds.get(id=r["rounds"][1]["id"])
        self.assertEqual(round_2.chronograms.valid().count(), 1)
        self.assertIsNone(round_2.chronograms.valid().first().created_by)

        round_one = r["rounds"][0]

        self.assertEqual(
            round_one["scopes"],
            [
                {
                    "vaccine": "bOPV",
                    "group": {
                        "name": f"scope {first_round.scopes.get(vaccine='bOPV').id} for round 1 campaign obr_name - bOPV",
                        "id": first_round.scopes.get(vaccine="bOPV").group.id,
                        "org_units": [o.id for o in first_round.scopes.get(vaccine="bOPV").group.org_units.all()],
                    },
                },
                {
                    "vaccine": "mOPV2",
                    "group": {
                        "name": f"scope {first_round.scopes.get(vaccine='mOPV2').id} for round 1 campaign obr_name - mOPV2",
                        "id": first_round.scopes.get(vaccine="mOPV2").group.id,
                        "org_units": [o.id for o in first_round.scopes.get(vaccine="mOPV2").group.org_units.all()],
                    },
                },
            ],
        )

    def test_changing_scope_type_deletes_old_scopes(self):
        # Create a new campaign with scope per campaign
        test_campaign, _, _, _, _, _ = self.create_campaign(
            obr_name="TEST_CAMPAIGN",
            account=self.account,
            source_version=self.source_version_1,
            country_ou_type=self.country_type,
            district_ou_type=self.district_type,
        )

        # Test that separate_scopes_per_round is False and campaign has scope
        self.client.force_authenticate(self.user)
        response = self.client.get(f"/api/polio/campaigns/{test_campaign.id}/")
        data = self.assertJSONResponse(response, 200)
        self.assertFalse(data["separate_scopes_per_round"])
        self.assertEqual(len(data["scopes"]), 1)
        self.assertEqual(len(data["scopes"][0]["group"]["org_units"]), 1)
        for r in data["rounds"]:
            self.assertEqual(len(r["scopes"]), 0)

        old_payload = {**data}

        # Format payload for campaign with round level scope (only on round 1)
        new_round_1 = data["rounds"][0]
        new_round_1["scopes"] = data["scopes"]
        new_rounds = [new_round_1, data["rounds"][1], data["rounds"][2]]
        payload = {**data, "separate_scopes_per_round": True, "rounds": new_rounds, "description": "Yabadabadoo"}

        # Test that scope is on round and not on campaign
        response = self.client.put(f"/api/polio/campaigns/{test_campaign.id}/", payload, format="json")
        data = self.assertJSONResponse(response, 200)
        self.assertTrue(data["separate_scopes_per_round"])
        self.assertEqual(len(data["scopes"]), 0)
        self.assertEqual(len(data["rounds"][0]["scopes"]), 1)
        self.assertEqual(len(data["rounds"][0]["scopes"][0]["group"]["org_units"]), 1)
        self.assertEqual(data["description"], "Yabadabadoo")
        for index, r in enumerate(data["rounds"]):
            if index > 0:
                self.assertEqual(len(r["scopes"]), 0)

        # Switch scope back to campaign level
        response = self.client.put(f"/api/polio/campaigns/{test_campaign.id}/", old_payload, format="json")
        data = self.assertJSONResponse(response, 200)
        self.assertFalse(data["separate_scopes_per_round"])
        self.assertEqual(len(data["scopes"]), 1)
        self.assertEqual(len(data["scopes"][0]["group"]["org_units"]), 1)
        for r in data["rounds"]:
            self.assertEqual(len(r["scopes"]), 0)

    def test_remove_round_deletes_round_in_DB(self):
        # Create a new campaign with scope per campaign
        test_campaign, _, _, _, _, _ = self.create_campaign(
            obr_name="TEST_CAMPAIGN",
            account=self.account,
            source_version=self.source_version_1,
            country_ou_type=self.country_type,
            district_ou_type=self.district_type,
        )

        # Call API to get payload
        self.client.force_authenticate(self.user)
        response = self.client.get(f"/api/polio/campaigns/{test_campaign.id}/")
        data = self.assertJSONResponse(response, 200)
        old_payload = {**data}
        rnds = old_payload["rounds"]
        # Keep the deleted round ddata so we can test against the ID
        rnd_to_delete = rnds.pop()
        # Format the paymoad to remove a round
        payload = {**old_payload, "rounds": rnds}

        response = self.client.put(f"/api/polio/campaigns/{test_campaign.id}/", payload, format="json")
        data = self.assertJSONResponse(response, 200)
        self.assertEqual(len(data["rounds"]), 2)
        self.assertIsNone(Round.objects.filter(id=rnd_to_delete["id"]).first())

    def test_campaign_creation_without_explicit_campaign_type(self):
        self.client.force_authenticate(self.user)
        payload = {
            "obr_name": "Test Campaign",
            "group": {"name": "Test Group", "org_units": []},
            "is_preventive": True,
            "is_test": False,
            "enable_send_weekly_email": False,
        }
        response = self.client.post("/api/polio/campaigns/", payload, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        campaign_id = response.data["id"]
        campaign = Campaign.objects.get(id=campaign_id)
        self.assertEqual(campaign.campaign_types.first().name, "Polio", "Campaign type should default to 'Polio'")

        response = self.client.get(f"/api/polio/campaigns/{campaign.id}/", format="json")
        self.assertEqual(response.status_code, 200, response.content)
        response_data = response.json()

        self.assertIn("campaign_types", response_data)
        campaign_types = response_data["campaign_types"]
        self.assertEqual(len(campaign_types), 1)

    def test_create_campaign_with_explicit_campaign_types(self):
        self.client.force_authenticate(self.user)
        self.assertEqual(Campaign.objects.count(), 0)

        campaign_type1 = CampaignType.objects.create(name="Type1")
        campaign_type2 = CampaignType.objects.create(name="Type2")
        payload = {
            "obr_name": "Campaign with Types",
            "group": {"name": "Test Group", "org_units": []},
            "is_preventive": True,
            "is_test": False,
            "enable_send_weekly_email": False,
            "campaign_types": [campaign_type1.id, campaign_type2.id],
        }

        response = self.client.post("/api/polio/campaigns/", payload, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        campaign_id = response.data["id"]
        campaign = Campaign.objects.get(id=campaign_id)

        self.assertEqual(campaign.campaign_types.count(), 2)
        self.assertTrue(campaign.campaign_types.filter(id=campaign_type1.id).exists())
        self.assertTrue(campaign.campaign_types.filter(id=campaign_type2.id).exists())

    def test_campaign_api_returns_campaign_types(self):
        self.client.force_authenticate(self.user)
        campaign_type1 = CampaignType.objects.create(name="Type1")
        campaign_type2 = CampaignType.objects.create(name="Type2")
        campaign_type_ids = [campaign_type1.id, campaign_type2.id]

        campaign = Campaign.objects.create(obr_name="Campaign with Types", account=self.account)
        campaign.campaign_types.set([campaign_type1, campaign_type2])

        response = self.client.get(f"/api/polio/campaigns/{campaign.id}/", format="json")
        self.assertEqual(response.status_code, 200, response.content)
        response_data = response.json()

        self.assertIn("campaign_types", response_data)
        campaign_types = response_data["campaign_types"]
        self.assertEqual(len(campaign_types), 2)

        self.assertIn(campaign_type1.id, campaign_type_ids)
        self.assertIn(campaign_type2.id, campaign_type_ids)

    def test_available_campaign_types(self):
        self.client.force_authenticate(self.user)
        campaign_types_count = CampaignType.objects.count()

        response = self.client.get("/api/polio/campaigns/available_campaign_types/", format="json")
        self.assertEqual(response.status_code, 200, response.content)
        response_data = response.json()

        self.assertEqual(len(response_data), campaign_types_count)
        self.assertIn(CampaignType.POLIO, [ct["name"] for ct in response_data])

    def test_filter_by_campaign_types(self):
        self.client.force_authenticate(self.user)
        campaign_type1 = CampaignType.objects.create(name="Type1")
        campaign_type2 = CampaignType.objects.create(name="Type2")
        campaign_type3 = CampaignType.objects.create(name="Type3")
        campaign1 = Campaign.objects.create(obr_name="Campaign1", account=self.account)
        campaign2 = Campaign.objects.create(obr_name="Campaign2", account=self.account)
        campaign3 = Campaign.objects.create(obr_name="Campaign3", account=self.account)
        campaign1.campaign_types.add(campaign_type1)
        campaign2.campaign_types.add(campaign_type2)
        campaign3.campaign_types.add(campaign_type3)

        # Filter by single campaign type
        response = self.client.get(f"/api/polio/campaigns/?campaign_types={campaign_type1.id}", format="json")
        self.assertEqual(response.status_code, 200, response.content)
        response_data = response.json()
        self.assertEqual(len(response_data), 1)
        self.assertEqual(response_data[0]["id"], str(campaign1.id))

        # Filter by single campaign type using slug
        response = self.client.get(f"/api/polio/campaigns/?campaign_types={campaign_type1.slug}", format="json")
        self.assertEqual(response.status_code, 200, response.content)
        response_data = response.json()
        self.assertEqual(len(response_data), 1)
        self.assertEqual(response_data[0]["id"], str(campaign1.id))

        # Filter by multiple campaign types
        response = self.client.get(
            f"/api/polio/campaigns/?campaign_types={campaign_type1.id},{campaign_type2.id}", format="json"
        )
        self.assertEqual(response.status_code, 200, response.content)
        response_data = response.json()
        self.assertEqual(len(response_data), 2)
        campaign_ids = [campaign["id"] for campaign in response_data]
        self.assertIn(str(campaign1.id), campaign_ids)
        self.assertIn(str(campaign2.id), campaign_ids)

        # Filter by multiple campaign types
        response = self.client.get(
            f"/api/polio/campaigns/?campaign_types={campaign_type1.slug},{campaign_type2.slug}", format="json"
        )
        self.assertEqual(response.status_code, 200, response.content)
        response_data = response.json()
        self.assertEqual(len(response_data), 2)
        campaign_ids = [campaign["id"] for campaign in response_data]
        self.assertIn(str(campaign1.id), campaign_ids)
        self.assertIn(str(campaign2.id), campaign_ids)

        # Filter by non-existing campaign type
        response = self.client.get("/api/polio/campaigns/?campaign_types=9999", format="json")
        self.assertEqual(response.status_code, 200, response.content)
        response_data = response.json()
        self.assertEqual(len(response_data), 0)

        # Filter by non-existing campaign type
        response = self.client.get("/api/polio/campaigns/?campaign_types=UNKNOWN_CAMPAIGN_TYPE", format="json")
        self.assertEqual(response.status_code, 200, response.content)
        response_data = response.json()
        self.assertEqual(len(response_data), 0)
