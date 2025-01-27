import django_filters
from rest_framework import serializers
from iaso.api.common import EtlModelViewset
from plugins.polio.api.permission_classes import PolioReadPermission
from plugins.polio.models.base import VaccineStockHistory
from django.utils.translation import gettext_lazy as _
from django.db.models.query import QuerySet


class VaccineStockHistoryDashboardSerializer(serializers.ModelSerializer):
    class Meta:
        model = VaccineStockHistory
        fields = "__all__"


class VaccineStockHistoryFilter(django_filters.rest_framework.FilterSet):
    vaccine = django_filters.CharFilter(method="filter_vaccine", label=_("Vaccine"))
    campaign = django_filters.CharFilter(method="filter_campaign", label=_("Campaign OBR name"))
    country = django_filters.NumberFilter(method="filter_country", label=_("Country ID"))
    round = django_filters.NumberFilter(method="filter_round", label=_("Round ID"))

    class Meta:
        model = VaccineStockHistory
        fields = "__all__"

    def filter_country(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        return queryset.filter(round__campaign__country=value)

    def filter_campaign(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        return queryset.filter(round__campaign__obr_name=value)

    def filter_vaccine(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        return queryset.filter(vaccine_stock__vaccine=value)

    def filter_round(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        return queryset.filter(round__id=value)


class VaccineStockHistoryDashboardViewSet(EtlModelViewset):
    """
    GET /api/polio/dashboards/vaccine_stock_history/
    Returns all Preparedness sheet snapshots
    Simple endpoint that returns all model fields to facilitate data manipulation by OpenHexa or PowerBI
    """

    http_method_names = ["get"]
    permission_classes = [PolioReadPermission]
    model = VaccineStockHistory
    serializer_class = VaccineStockHistoryDashboardSerializer
    filterset_class = VaccineStockHistoryFilter
    ordering_fields = ["created_at"]

    def get_queryset(self):
        return VaccineStockHistory.objects.filter_for_user(self.request.user)
