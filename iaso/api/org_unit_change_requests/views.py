import csv
from datetime import datetime

import django_filters
from django.db.models import Prefetch
from django.http import HttpResponse

from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from iaso.api.common import CONTENT_TYPE_CSV
from iaso.api.org_unit_change_requests.filters import OrgUnitChangeRequestListFilter
from iaso.api.org_unit_change_requests.pagination import OrgUnitChangeRequestPagination
from iaso.api.org_unit_change_requests.permissions import (
    HasOrgUnitsChangeRequestPermission,
    HasOrgUnitsChangeRequestReviewPermission,
)
from iaso.api.org_unit_change_requests.serializers import (
    OrgUnitChangeRequestListSerializer,
    OrgUnitChangeRequestRetrieveSerializer,
    OrgUnitChangeRequestReviewSerializer,
    OrgUnitChangeRequestWriteSerializer,
    OrgUnitChangeRequestBulkReviewSerializer,
)
from iaso.api.serializers import AppIdSerializer
from iaso.api.tasks.serializers import TaskSerializer
from iaso.models import OrgUnit, OrgUnitChangeRequest, Instance
from iaso.tasks.org_unit_change_requests_bulk_review import (
    org_unit_change_requests_bulk_approve,
    org_unit_change_requests_bulk_reject,
)
from iaso.utils.models.common import get_creator_name


class OrgUnitChangeRequestViewSet(viewsets.ModelViewSet):
    filter_backends = [filters.OrderingFilter, django_filters.rest_framework.DjangoFilterBackend]
    filterset_class = OrgUnitChangeRequestListFilter
    ordering_fields = [
        "id",
        "org_unit__name",
        "org_unit__parent__name",
        "org_unit__org_unit_type__name",
        "groups",
        "created_at",
        "updated_at",
        "status",
        "created_by__username",
        "updated_by__username",
    ]
    http_method_names = ["get", "options", "patch", "post", "head", "trace"]
    pagination_class = OrgUnitChangeRequestPagination

    def get_permissions(self):
        if self.action in ["partial_update", "bulk_review"]:
            permission_classes = [HasOrgUnitsChangeRequestReviewPermission]
        else:
            permission_classes = [HasOrgUnitsChangeRequestPermission]
        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        if self.action in ["create"]:
            return OrgUnitChangeRequestWriteSerializer
        if self.action in ["list", "metadata"]:
            return OrgUnitChangeRequestListSerializer
        if self.action == "retrieve":
            return OrgUnitChangeRequestRetrieveSerializer
        if self.action == "partial_update":
            return OrgUnitChangeRequestReviewSerializer

    def get_queryset(self):
        org_units = OrgUnit.objects.filter_for_user(self.request.user)
        org_units_change_requests = (
            OrgUnitChangeRequest.objects.select_related(
                "created_by",
                "updated_by",
                "org_unit__parent",
                "org_unit__org_unit_type",
                "new_parent",
                "old_parent",
                "new_org_unit_type",
                "old_org_unit_type",
                "org_unit__version",
                "data_source_synchronization",
            )
            .prefetch_related(
                "org_unit__groups",
                Prefetch("org_unit__reference_instances", queryset=Instance.non_deleted_objects.select_related("form")),
                "org_unit__reference_instances__form",
                "new_groups",
                "old_groups",
                Prefetch("new_reference_instances", queryset=Instance.non_deleted_objects.select_related("form")),
                Prefetch("old_reference_instances", queryset=Instance.non_deleted_objects.select_related("form")),
                "org_unit__org_unit_type__projects",
            )
            .exclude_soft_deleted_new_reference_instances()
        )

        return org_units_change_requests.filter(org_unit__in=org_units)

    def has_org_unit_permission(self, org_unit_to_change: OrgUnit) -> None:
        # The mobile adds `?app_id=.bar.baz` in the query params.
        app_id_serializer = AppIdSerializer(data=self.request.query_params)
        app_id_serializer.is_valid()
        app_id = app_id_serializer.validated_data.get("app_id")
        org_units_for_user = OrgUnit.objects.filter_for_user_and_app_id(self.request.user, app_id)
        if not org_units_for_user.filter(id=org_unit_to_change.pk).exists():
            raise PermissionDenied("The user is trying to create a change request for an unauthorized OrgUnit.")

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        # Allow the front-end to know the total number of change requests with the status "new" that can be used in bulk review.
        response.data["select_all_count"] = (
            self.filter_queryset(self.get_queryset()).filter(status=OrgUnitChangeRequest.Statuses.NEW).count()
        )
        return response

    def perform_create(self, serializer):
        """
        POST to create an `OrgUnitChangeRequest`.
        """
        org_unit_to_change = serializer.validated_data["org_unit"]
        self.has_org_unit_permission(org_unit_to_change)
        serializer.validated_data["created_by"] = self.request.user
        serializer.save()

    def partial_update(self, request, *args, **kwargs):
        """
        PATCH to approve or reject an `OrgUnitChangeRequest`.
        """
        change_request = self.get_object()

        self.has_org_unit_permission(change_request.org_unit)
        if change_request.status != change_request.Statuses.NEW:
            raise ValidationError(
                f"Status must be `{change_request.Statuses.NEW}` but current status is `{change_request.status}`."
            )

        serializer = self.get_serializer(change_request, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        status = serializer.validated_data["status"]
        rejection_comment = serializer.validated_data.get("rejection_comment", "")

        if status == change_request.Statuses.APPROVED:
            change_request.approve(
                user=self.request.user,
                approved_fields=serializer.validated_data["approved_fields"],
                rejection_comment=rejection_comment,
            )

        if status == change_request.Statuses.REJECTED:
            change_request.reject(
                user=self.request.user,
                rejection_comment=rejection_comment,
            )

        response_serializer = OrgUnitChangeRequestRetrieveSerializer(change_request)
        return Response(response_serializer.data)

    @action(detail=False, methods=["patch"])
    def bulk_review(self, request):
        serializer = OrgUnitChangeRequestBulkReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        selected_ids = serializer.validated_data["selected_ids"]
        unselected_ids = serializer.validated_data["unselected_ids"]
        status = serializer.validated_data["status"]
        approved_fields = serializer.validated_data["approved_fields"]
        rejection_comment = serializer.validated_data["rejection_comment"]

        queryset = self.filter_queryset(self.get_queryset()).filter(status=OrgUnitChangeRequest.Statuses.NEW)

        if selected_ids:
            queryset = queryset.filter(pk__in=selected_ids)

        if unselected_ids:
            queryset = queryset.exclude(pk__in=unselected_ids)

        ids = list(queryset.values_list("pk", flat=True))

        if status == OrgUnitChangeRequest.Statuses.APPROVED:
            task = org_unit_change_requests_bulk_approve(
                change_requests_ids=ids, approved_fields=list(approved_fields), user=self.request.user
            )
        else:
            task = org_unit_change_requests_bulk_reject(
                change_requests_ids=ids, rejection_comment=rejection_comment, user=self.request.user
            )

        return Response({"task": TaskSerializer(instance=task).data})

    @staticmethod
    def org_unit_change_request_csv_columns():
        return [
            "Id",
            "Name",
            "Parent",
            "Org unit type",
            "Groups",
            "Status",
            "Created",
            "Created by",
            "Updated",
            "Updated by",
        ]

    @action(detail=False, methods=["get"])
    def export_to_csv(self, request):
        filename = "%s--%s" % ("review-change-proposals", datetime.now().strftime("%Y-%m-%d"))
        org_unit_changes_requests = self.get_queryset().order_by("org_unit__name")
        filtered_org_unit_changes_requests = OrgUnitChangeRequestListFilter(
            request.GET, queryset=org_unit_changes_requests
        ).qs

        response = HttpResponse(content_type=CONTENT_TYPE_CSV)

        writer = csv.writer(response)
        headers = self.org_unit_change_request_csv_columns()
        writer.writerow(headers)

        for change_request in filtered_org_unit_changes_requests:
            row = [
                change_request.id,
                change_request.org_unit.name,
                change_request.org_unit.parent.name if change_request.org_unit.parent else None,
                change_request.org_unit.org_unit_type.name,
                ",".join(group.name for group in change_request.org_unit.groups.all()),
                change_request.get_status_display(),
                datetime.strftime(change_request.created_at, "%Y-%m-%d"),
                get_creator_name(change_request.created_by) if change_request.created_by else None,
                datetime.strftime(change_request.updated_at, "%Y-%m-%d"),
                get_creator_name(change_request.updated_by) if change_request.updated_by else None,
            ]
            writer.writerow(row)
        filename = filename + ".csv"
        response["Content-Disposition"] = "attachment; filename=" + filename
        return response
