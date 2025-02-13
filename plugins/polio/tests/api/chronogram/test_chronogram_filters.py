import datetime

import time_machine

from iaso.test import APITestCase

from plugins.polio.api.chronogram.filters import filter_for_power_bi
from plugins.polio.models import Chronogram


TODAY = datetime.datetime(2024, 8, 23, 16, 0, 0, 0, tzinfo=datetime.timezone.utc)


@time_machine.travel(TODAY, tick=False)
class ChronogramFiltersTestCase(APITestCase):
    """
    Test Chronogram Filters.
    """

    def test_filter_for_power_bi(self):
        queryset = filter_for_power_bi(Chronogram.objects.all())

        three_months_ago = "2024-05-23 16:00:00+00:00"
        sql_query = str(queryset.query)

        self.assertIn(f'"created_at" >= {three_months_ago}', sql_query)
