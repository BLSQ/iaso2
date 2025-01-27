from rest_framework import serializers
from iaso.api.common import EtlModelViewset
from plugins.polio.api.permission_classes import PolioReadPermission
from plugins.polio.models import SpreadSheetImport


class SpreadSheetImportDashboardSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpreadSheetImport
        fields = "__all__"


class SpreadSheetImportViewSet(EtlModelViewset):
    """
    GET /api/polio/dashboards/preparedness_sheets/
    Returns all Preparedness sheet snapshots
    Simple endpoint that returns all model fields to facilitate data manipulation by OpenHexa or PowerBI
    """

    http_method_names = ["get"]
    permission_classes = [PolioReadPermission]
    model = SpreadSheetImport
    serializer_class = SpreadSheetImportDashboardSerializer

    def get_queryset(self):
        # can't filter on account since model has no account field
        return SpreadSheetImport.objects.all().order_by("url")
