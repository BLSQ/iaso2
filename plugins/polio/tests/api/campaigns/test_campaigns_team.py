from django.contrib.auth.models import Permission, User

from hat.audit.models import Modification
from iaso.test import APITestCase
from plugins.polio.preparedness.spreadsheet_manager import *


class TeamAPITestCase(APITestCase):
    fixtures = ["user.yaml"]
    c: Campaign
    user: User
    country: OrgUnit
    country2: OrgUnit

    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = User.objects.get(username="test")
        cls.country = OrgUnit.objects.create(name="Country A")
        cls.country2 = OrgUnit.objects.create(name="Country B")

        cls.c = Campaign.objects.create(
            obr_name="test campaign", account=cls.user.iaso_profile.account, country=cls.country
        )

    def test_audit_list(self):
        """Mod a campaign, user can see modification. Limit to another country modification cannot be listed anymore
        Give access to country in campaign , they can be listed again
        """
        self.client.force_authenticate(self.user)
        self.assertEqual(self.user.is_superuser, False)
        self.user.user_permissions.add(Permission.objects.get(codename="iaso_polio"))
        payload = {"obr_name": "test2"}
        response = self.client.put(f"/api/polio/campaigns/{self.c.id}/", payload, format="json")
        self.assertJSONResponse(response, 200)

        self.assertEqual(Modification.objects.count(), 1)
        response = self.client.get(f"/api/logs/?objectId={self.c.id}&contentType=polio.campaign&limit=10")
        j = self.assertJSONResponse(response, 200)
        self.assertEqual(len(j["list"]), 1)

        # limit user to the other country. Cannot list
        p = self.user.iaso_profile
        p.org_units.set([self.country2])
        p.save()
        response = self.client.get(f"/api/logs/?objectId={self.c.id}&contentType=polio.campaign&limit=10")
        j = self.assertJSONResponse(response, 401)
        self.assertEqual(j, {"error": "Unauthorized"})

        # limit user to the other country. Cannot list
        p = self.user.iaso_profile
        p.org_units.set([self.c.country])
        p.save()
        self.client.force_authenticate(self.user)

        response = self.client.get(f"/api/logs/?objectId={self.c.id}&contentType=polio.campaign&limit=10")
        j = self.assertJSONResponse(response, 200)
        self.assertEqual(len(j["list"]), 1)
