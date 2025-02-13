import datetime

import time_machine

from iaso import models as m
from iaso.test import APITestCase

from plugins.polio.models import Campaign, Round, CampaignScope

TODAY = datetime.datetime(2024, 10, 21, 11, 0, 0, 0, tzinfo=datetime.timezone.utc)


@time_machine.travel(TODAY, tick=False)
class CsvCampaignScopesExportViewTestCase(APITestCase):
    """
    Test CampaignViewSet.csv_campaign_scopes_export.
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
        )

        cls.org_unit_a = m.OrgUnit.objects.create(
            name="A",
            org_unit_type=m.OrgUnitType.objects.create(category="COUNTRY"),
            validation_status=m.OrgUnit.VALIDATION_VALID,
            version=cls.source_version,
        )
        cls.org_unit_b = m.OrgUnit.objects.create(
            name="B",
            org_unit_type=m.OrgUnitType.objects.create(category="REGION"),
            validation_status=m.OrgUnit.VALIDATION_VALID,
            version=cls.source_version,
            parent=cls.org_unit_a,
        )
        cls.org_unit_c = m.OrgUnit.objects.create(
            name="C",
            org_unit_type=m.OrgUnitType.objects.create(category="DISTRICT"),
            validation_status=m.OrgUnit.VALIDATION_VALID,
            version=cls.source_version,
            parent=cls.org_unit_b,
        )

        cls.group = m.Group.objects.create(name="Group", domain="POLIO", source_version=cls.source_version)
        cls.group.org_units.add(cls.org_unit_a)
        cls.group.org_units.add(cls.org_unit_b)
        cls.group.org_units.add(cls.org_unit_c)

        cls.campaign = Campaign.objects.create(obr_name="Campaign OBR name", account=cls.account)
        cls.round = Round.objects.create(number=1, campaign=cls.campaign, started_at=TODAY.date())
        cls.campaign_scope = CampaignScope.objects.create(campaign=cls.campaign, group=cls.group)

    def test_get_csv_campaign_scopes_export_ok(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(f"/api/polio/campaigns/csv_campaign_scopes_export/?&round={self.round.pk}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get("Content-Disposition"),
            "attachment; filename=campaign-Campaign OBR name--R1--org_units-2024-10-21-11-00.csv",
        )

        response_csv = response.getvalue().decode("utf-8")
        expected_csv = (
            "ID,Admin 2,Admin 1,Admin 0,OBR Name,Round Number,Start date,Vaccine\r\n"
            f"{self.org_unit_a.pk},A,,,Campaign OBR name,R1,2024-10-21,\r\n"
            f"{self.org_unit_b.pk},B,A,,Campaign OBR name,R1,2024-10-21,\r\n"
            f"{self.org_unit_c.pk},C,B,A,Campaign OBR name,R1,2024-10-21,\r\n"
        )
        self.assertEqual(response_csv, expected_csv)
