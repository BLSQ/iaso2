from datetime import datetime, timedelta

from rest_framework import status

from iaso import models as m
from iaso.test import APITestCase
from plugins.polio.models import Campaign, ReasonForDelay, Round, RoundDateHistoryEntry


class PolioReasonSForDelayTestCase(APITestCase):
    @classmethod
    def setUp(cls):
        cls.url = "/api/polio/reasonsfordelay/"
        cls.campaign_url = "/api/polio/reasonsfordelay/forcampaign/"
        cls.account = account = m.Account.objects.create(name="test account")
        cls.other_account = m.Account.objects.create(name="other account")
        cls.project = m.Project.objects.create(
            name="Polio", app_id="polio.rapid.outbreak.taskforce", account=cls.account
        )
        cls.data_source = m.DataSource.objects.create(name="Default source")
        cls.data_source.projects.add(cls.project)
        cls.data_source.save()
        cls.source_version = m.SourceVersion.objects.create(data_source=cls.data_source, number=1)
        cls.source_version.save()
        cls.country_org_unit_1 = m.OrgUnit.objects.create(
            name="Country1",
            validation_status=m.OrgUnit.VALIDATION_VALID,
            source_ref="PvtAI4RUMkr",
            version=cls.source_version,
        )
        cls.country_org_unit_1.save()
        cls.country_org_unit_2 = m.OrgUnit.objects.create(
            name="Country2",
            validation_status=m.OrgUnit.VALIDATION_VALID,
            source_ref="PvtAI4RUMkr",
            version=cls.source_version,
        )
        cls.country_org_unit_2.save()
        cls.polio_admin_user = cls.create_user_with_profile(
            username="test admin user", account=account, permissions=["iaso_polio_config"]
        )
        cls.polio_user = cls.create_user_with_profile(username="test user", account=account, permissions=["iaso_polio"])
        cls.round1_start = (datetime.now() - timedelta(days=42)).date()
        cls.round1_end = (datetime.now() - timedelta(days=39)).date()
        cls.campaign = Campaign.objects.create(
            obr_name="right_campaign", account=account, initial_org_unit=cls.country_org_unit_1
        )
        cls.round1 = Round.objects.create(
            number=1,
            started_at=cls.round1_start.strftime("%Y-%m-%d"),
            ended_at=cls.round1_end.strftime("%Y-%m-%d"),
            campaign=cls.campaign,
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
        cls.i_cant_i_go_swimming = ReasonForDelay.objects.create(
            account=cls.other_account,
            key_name="I_CANT_I_GO_SWIMMING",
            name_en="I can't I go swimming",
            name_fr="Je peux pas j'ai piscine",
        )
        cls.round1_modif1 = RoundDateHistoryEntry.objects.create(round=cls.round1, reason_for_delay=cls.initial_data)
        cls.round1_modif2 = RoundDateHistoryEntry.objects.create(
            round=cls.round1, reason_for_delay=cls.cat_ate_my_homework
        )
        cls.round1_modif3 = RoundDateHistoryEntry.objects.create(
            round=cls.round1, reason_for_delay=cls.cat_ate_my_homework
        )

    def test_no_perm(self):
        user_no_perm = self.create_user_with_profile(username="test user2", account=self.account, permissions=[])
        self.client.force_authenticate(user_no_perm)
        response = self.client.get(self.url)
        jr = self.assertJSONResponse(response, 403)
        self.assertEqual({"detail": "You do not have permission to perform this action."}, jr)

        self.client.force_authenticate(self.polio_user)
        response = self.client.get(self.url)
        jr = self.assertJSONResponse(response, 403)
        self.assertEqual({"detail": "You do not have permission to perform this action."}, jr)

    def test_list_for_campaigns(self):
        self.client.force_authenticate(self.polio_user)
        response = self.client.get(self.campaign_url)
        jr = self.assertJSONResponse(response, 200)
        results = jr["results"]
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["key_name"], self.initial_data.key_name)
        self.assertEqual(results[0]["name_en"], self.initial_data.name_en)
        self.assertEqual(results[0]["name_fr"], self.initial_data.name_fr)
        self.assertEqual(results[1]["key_name"], self.cat_ate_my_homework.key_name)
        self.assertEqual(results[1]["name_en"], self.cat_ate_my_homework.name_en)
        self.assertEqual(results[1]["name_fr"], self.cat_ate_my_homework.name_fr)

    def test_get_list(self):
        self.client.force_authenticate(self.polio_admin_user)
        response = self.client.get(self.url)
        jr = self.assertJSONResponse(response, 200)
        results = jr["results"]
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["key_name"], self.initial_data.key_name)
        self.assertEqual(results[0]["name_en"], self.initial_data.name_en)
        self.assertEqual(results[0]["name_fr"], self.initial_data.name_fr)
        self.assertEqual(results[0]["times_selected"], 1)
        self.assertEqual(results[1]["key_name"], self.cat_ate_my_homework.key_name)
        self.assertEqual(results[1]["name_en"], self.cat_ate_my_homework.name_en)
        self.assertEqual(results[1]["name_fr"], self.cat_ate_my_homework.name_fr)
        self.assertEqual(results[1]["times_selected"], 2)

    def test_create(self):
        self.client.force_authenticate(self.polio_admin_user)
        key_name = "I_LEFT_IT_AT_HOME"
        name_en = "I left it at home"
        name_fr = "Je l'ai oublié à la maison"
        response = self.client.post(
            self.url,
            format="json",
            data={
                "key_name": key_name,
                "name_en": name_en,
                "name_fr": name_fr,
            },
        )
        jr = self.assertJSONResponse(response, 201)
        self.assertEqual(jr["key_name"], key_name)
        self.assertEqual(jr["name_en"], name_en)
        self.assertEqual(jr["name_fr"], name_fr)
        self.assertEqual(jr["times_selected"], 0)

    def test_update(self):
        self.client.force_authenticate(self.polio_admin_user)
        new_name_en = "Meow"
        response = self.client.patch(
            f"{self.url}{self.cat_ate_my_homework.id}/",
            format="json",
            data={
                "name_en": new_name_en,
            },
        )
        jr = self.assertJSONResponse(response, 200)

        self.assertEqual(jr["key_name"], self.cat_ate_my_homework.key_name)
        self.assertEqual(jr["name_en"], new_name_en)
        self.assertEqual(jr["name_fr"], self.cat_ate_my_homework.name_fr)

    def test_wrong_account(self):
        self.client.force_authenticate(
            self.create_user_with_profile(
                username="test user2", account=self.other_account, permissions=["iaso_polio_config"]
            )
        )
        new_name_en = "Meow"
        response = self.client.patch(
            f"{self.url}{self.cat_ate_my_homework.id}/",
            format="json",
            data={
                "name_en": new_name_en,
            },
        )
        self.assertContains(
            response, "No ReasonForDelay matches the given query", status_code=status.HTTP_404_NOT_FOUND
        )
