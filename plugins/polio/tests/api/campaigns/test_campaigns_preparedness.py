from django.utils import timezone

from rest_framework.test import APIClient

from iaso import models as m
from iaso.models import Account
from iaso.test import APITestCase
from plugins.polio.models import CampaignType
from plugins.polio.preparedness.spreadsheet_manager import *


class PreparednessAPITestCase(APITestCase):
    data_source: m.DataSource
    source_version_1: m.SourceVersion
    account: Account

    @classmethod
    def setUpTestData(cls):
        cls.data_source = m.DataSource.objects.create(name="Default source")
        cls.now = timezone.now()
        cls.source_version_1 = m.SourceVersion.objects.create(data_source=cls.data_source, number=1)
        cls.account = Account.objects.create(name="polio", default_version=cls.source_version_1)
        cls.user = cls.create_user_with_profile(username="user", account=cls.account, permissions=["iaso_forms"])

    def setUp(self):
        """Make sure we have a fresh client at the beginning of each test"""
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_two_campaign_round_empty(self):
        type, created = CampaignType.objects.get_or_create(name=CampaignType.POLIO)
        campaign_a = Campaign.objects.create(obr_name="campaign A", account=self.account)
        campaign_a.campaign_types.add(type)
        campaign_a.rounds.create(number=1)
        campaign_a.rounds.create(number=3)
        Campaign.objects.create(obr_name="campaign B", account=self.account)
        Campaign.objects.create(obr_name="campaign c", account=self.account)

        response = self.client.get(f"/api/polio/campaigns/{campaign_a.id}/", format="json")

        r = self.assertJSONResponse(response, 200)
        self.assertEqual(len(r["rounds"]), 2)

        response = self.client.get(f"/api/polio/preparedness_dashboard/", format="json")
        r = self.assertJSONResponse(response, 200)
        self.assertEqual(len(r), 0)

    def test_two_campaign_round_error(self):
        type, created = CampaignType.objects.get_or_create(name=CampaignType.POLIO)
        campaign_a = Campaign.objects.create(obr_name="campaign A", account=self.account)
        campaign_a.campaign_types.add(type)
        round_one = campaign_a.rounds.create(number=1)
        round_three = campaign_a.rounds.create(number=3)
        campaign_b = Campaign.objects.create(obr_name="campaign B", account=self.account)
        campaign_c = Campaign.objects.create(obr_name="campaign c", account=self.account)
        campaign_b.campaign_types.add(type)
        campaign_c.campaign_types.add(type)
        response = self.client.get(f"/api/polio/campaigns/{campaign_a.id}/", format="json")

        r = self.assertJSONResponse(response, 200)
        self.assertEqual(len(r["rounds"]), 2)

        round_one.preparedness_spreadsheet_url = "https://docs.google.com/spreadsheets/d/1"
        round_one.save()
        round_three.preparedness_spreadsheet_url = "https://docs.google.com/spreadsheets/d/1"
        round_three.save()

        response = self.client.get(f"/api/polio/preparedness_dashboard/", format="json")
        r = self.assertJSONResponse(response, 200)
        self.assertEqual(len(r), 2)
        for campaign_round in r:
            self.assertEqual(campaign_round["status"], "not_sync")

        """[{'campaign_id': '6ecda204-2206-4ae2-a38a-5359684dccf6', 'campaign_obr_name': 'campaign A',
          'indicators': {}, 'round': 'Round1', 'round_id': 44, 'round_start': None, 'round_end': None,
          'status': 'not_sync', 'details': 'This spreadsheet has not been synchronised yet'}, {
                'campaign_id': '6ecda204-2206-4ae2-a38a-5359684dccf6', 'campaign_obr_name': 'campaign A',
                'indicators': {}, 'round': 'Round3', 'round_id': 45, 'round_start': None, 'round_end': None,
                'status': 'not_sync', 'details': 'This spreadsheet has not been synchronised yet'}]"""
