import django_filters

from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.request import Request

from iaso.api.data_source_versions_synchronization.filters import DataSourceVersionsSynchronizationFilter
from iaso.api.data_source_versions_synchronization.pagination import DataSourceVersionsSynchronizationPagination
from iaso.api.data_source_versions_synchronization.permissions import DataSourceVersionsSynchronizationPermission
from iaso.api.data_source_versions_synchronization.serializers import (
    DataSourceVersionsSynchronizationSerializer,
    CreateJsonDiffParametersSerializer,
)
from iaso.api.tasks.serializers import TaskSerializer
from iaso.models import DataSourceVersionsSynchronization
from iaso.tasks.data_source_versions_synchronization import synchronize_source_versions_async


class DataSourceVersionsSynchronizationViewSet(viewsets.ModelViewSet):
    filter_backends = [filters.OrderingFilter, django_filters.rest_framework.DjangoFilterBackend]
    filterset_class = DataSourceVersionsSynchronizationFilter
    ordering_fields = [
        "id",
        "name",
        "count_create",
        "count_update",
        "account",
        "created_by__username",
        "created_at",
        "updated_at",
    ]
    http_method_names = ["get", "options", "patch", "post", "head", "trace"]
    pagination_class = DataSourceVersionsSynchronizationPagination
    permission_classes = [DataSourceVersionsSynchronizationPermission]
    serializer_class = DataSourceVersionsSynchronizationSerializer

    def get_queryset(self):
        account = self.request.user.iaso_profile.account
        return (
            DataSourceVersionsSynchronization.objects.select_related(
                "source_version_to_update__data_source",
                "source_version_to_compare_with__data_source",
                "account",
                "created_by",
            )
            .filter(account=account)
            .order_by("-id")
        )

    def perform_create(self, serializer: DataSourceVersionsSynchronizationSerializer) -> None:
        """
        Steps to synchronize data source versions:

        1. POST on this endpoint to create a new `DataSourceVersionsSynchronization`
        2. PATCH on the `create_json_diff_async` endpoint to compute the differences asynchronously
        3. PATCH on the `synchronize_source_versions_async` endpoint to create change requests asynchronously
        """
        serializer.validated_data["account"] = self.request.user.iaso_profile.account
        serializer.validated_data["created_by"] = self.request.user
        serializer.save()

    @action(detail=True, methods=["PATCH"])
    def create_json_diff(self, request: Request, pk: int) -> Response:
        data_source_versions_synchronization = get_object_or_404(self.get_queryset(), pk=pk)
        if data_source_versions_synchronization.change_requests.exists():
            raise ValidationError("Change requests have already been created.")

        json_diff_params_serializer = CreateJsonDiffParametersSerializer(
            data=self.request.data,
            context={"data_source_versions_synchronization": data_source_versions_synchronization},
        )
        json_diff_params_serializer.is_valid(raise_exception=True)
        json_diff_params = json_diff_params_serializer.validated_data

        data_source_versions_synchronization.create_json_diff(**json_diff_params)
        return Response(self.serializer_class(instance=data_source_versions_synchronization).data)

    @action(detail=True, methods=["PATCH"])
    def synchronize_source_versions_async(self, request: Request, pk: int) -> Response:
        data_source_versions_synchronization = get_object_or_404(self.get_queryset(), pk=pk)

        if not data_source_versions_synchronization.json_diff:
            raise ValidationError("Cannot synchronize data source versions because JSON diff is empty.")

        if data_source_versions_synchronization.change_requests.exists():
            raise ValidationError("Change requests have already been created.")

        task = synchronize_source_versions_async(
            data_source_versions_synchronization_id=data_source_versions_synchronization.pk, user=request.user
        )
        return Response({"task": TaskSerializer(instance=task).data})
