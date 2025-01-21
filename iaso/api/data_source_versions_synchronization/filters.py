import django_filters

from django.utils.translation import gettext_lazy as _

from iaso.models import DataSourceVersionsSynchronization


class DataSourceVersionsSynchronizationFilter(django_filters.rest_framework.FilterSet):
    created_at__gte = django_filters.IsoDateTimeFilter(
        field_name="created_at", lookup_expr="gte", label=_("Created at greater than or equal to")
    )

    class Meta:
        model = DataSourceVersionsSynchronization
        fields = {
            "id": ["exact"],
            "name": ["icontains"],
            "created_by": ["exact"],
        }
