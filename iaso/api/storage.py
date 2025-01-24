# TODO: need better type annotations in this file
import datetime
from typing import Tuple, Union, List, Any

from django.core.paginator import Paginator
from django.db.models import Prefetch, QuerySet, Q
from django.http import HttpResponse, StreamingHttpResponse
from rest_framework import viewsets, permissions, serializers, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.fields import Field
from rest_framework.mixins import CreateModelMixin, ListModelMixin
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from hat.api.export_utils import generate_xlsx, iter_items, Echo, timestamp_to_utc_datetime
from iaso.api.entity import EntitySerializer
from iaso.api.serializers import OrgUnitSerializer
from iaso.models import StorageLogEntry, StorageDevice, Instance, OrgUnit, Entity
from .common import (
    TimestampField,
    HasPermission,
    UserSerializer,
    CONTENT_TYPE_XLSX,
    CONTENT_TYPE_CSV,
    EXPORTS_DATETIME_FORMAT,
    safe_api_import,
)
from .instances import FileFormatEnum
from hat.menupermissions import models as permission


class EntityNestedSerializer(EntitySerializer):
    class Meta:
        model = Entity
        fields = ["id", "name"]


class StorageOrgUnitNestedSerializer(OrgUnitSerializer):
    class Meta:
        model = OrgUnit
        fields = [
            "id",
            "name",
        ]


class StorageLogSerializer(serializers.ModelSerializer):
    storage_id = serializers.CharField(source="device.customer_chosen_id")
    storage_type = serializers.CharField(source="device.type")
    entity = EntityNestedSerializer(read_only=True)
    org_unit = StorageOrgUnitNestedSerializer(read_only=True)
    performed_at = TimestampField(read_only=True)
    performed_by = UserSerializer(read_only=True)

    class Meta:
        model = StorageLogEntry
        fields = [
            "id",
            "storage_id",
            "storage_type",
            "operation_type",
            "instances",
            "org_unit",
            "entity",
            "performed_at",
            "performed_by",
            "status",
            "status_reason",
            "status_comment",
        ]


class StorageStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=StorageDevice.STATUS_CHOICES)
    reason = serializers.ChoiceField(
        source="status_reason", required=False, choices=StorageDevice.STATUS_REASON_CHOICES
    )
    updated_at: Field = serializers.DateTimeField(source="status_updated_at", read_only=True)
    comment = serializers.CharField(source="status_comment", required=False, allow_blank=True)

    def to_representation(self, obj):
        ret = super(StorageStatusSerializer, self).to_representation(obj)

        # If status is OK, we don't want to return the reason nor the comment
        if obj.status == StorageDevice.OK:
            ret.pop("reason")
            ret.pop("comment")

        return ret

    def validate(self, data):
        """
        Ensure that a reason is set if changed to a non-ok status
        """
        missing_status_reason = True
        if "status_reason" in data and data["status_reason"] != "":
            missing_status_reason = False

        if data["status"] != StorageDevice.OK and missing_status_reason:
            raise serializers.ValidationError("A reason must be provided when changing the status to a non-ok status")
        return data


class StorageStatusSerializerForMobile(StorageStatusSerializer):
    """Like StorageStatusSerializer, but updated_at is a timestamp instead of a datetime"""

    updated_at = TimestampField(source="status_updated_at", read_only=True)


class StorageSerializer(serializers.ModelSerializer):
    storage_id = serializers.CharField(source="customer_chosen_id")
    storage_type = serializers.CharField(source="type")
    storage_status = StorageStatusSerializer(source="*")
    entity = EntityNestedSerializer(read_only=True)
    org_unit = StorageOrgUnitNestedSerializer(read_only=True)
    created_at = TimestampField(read_only=True)
    updated_at = TimestampField(read_only=True)

    class Meta:
        model = StorageDevice
        fields: Tuple[str, ...] = (
            "updated_at",
            "created_at",
            "storage_id",
            "storage_type",
            "storage_status",
            "org_unit",
            "entity",
        )


class StorageSerializerWithLogs(StorageSerializer):
    """
    Like StorageSerializer, but also includes the log entries

    Requires a "filtered_log_entries" attribute on the data, use a Prefetch() object
    """

    logs: Field = StorageLogSerializer(many=True, source="filtered_log_entries")

    class Meta(StorageSerializer.Meta):
        fields = StorageSerializer.Meta.fields + ("logs",)


class StorageSerializerWithPaginatedLogs(StorageSerializerWithLogs):
    """
    Extends StorageSerializerWithLogs so the log entries can be paginated

    Requires:
     - a "filtered_log_entries" attribute on the data, use a Prefetch() object
     - "limit" and "offset" in the serializer context
    """

    logs = serializers.SerializerMethodField(method_name="get_filtered_and_paginated_log_entries")

    def get_filtered_and_paginated_log_entries(self, obj):
        offset = self.context["offset"]
        limit = self.context["limit"]
        logs = obj.filtered_log_entries[offset : offset + limit]
        return StorageLogSerializer(logs, many=True).data


def device_generate_export(
    queryset: "QuerySet[StorageDevice]", file_format: FileFormatEnum
) -> Union[HttpResponse, StreamingHttpResponse]:
    columns = [
        {"title": "Storage ID"},
        {"title": "Storage Type"},
        {"title": "Created at"},
        {"title": "Updated at"},
        {"title": "Status"},
        {"title": "Status reason"},
        {"title": "Status comment"},
        {"title": "Status updated at"},
        {"title": "Org unit id"},
        {"title": "Entity id"},
    ]

    def get_row(device: StorageDevice, **_) -> List[Any]:
        created_at_str = ""
        if device.created_at is not None:
            created_at_str = device.created_at.strftime(EXPORTS_DATETIME_FORMAT)

        updated_at_str = ""
        if device.updated_at is not None:
            updated_at_str = device.updated_at.strftime(EXPORTS_DATETIME_FORMAT)

        return [
            device.customer_chosen_id,
            device.type,
            created_at_str,
            updated_at_str,
            device.status,
            device.status_reason,
            device.status_comment,
            device.status_updated_at,
            device.org_unit_id,
            device.entity_id,
        ]

    response: Union[HttpResponse, StreamingHttpResponse]
    filename = "storage_devices"
    if file_format == FileFormatEnum.XLSX:
        filename = filename + ".xlsx"
        response = HttpResponse(
            generate_xlsx("Devices", columns, queryset, get_row),
            content_type=CONTENT_TYPE_XLSX,
        )
    else:
        filename = filename + ".csv"
        response = StreamingHttpResponse(
            streaming_content=(iter_items(queryset, Echo(), columns, get_row)), content_type=CONTENT_TYPE_CSV
        )

    response["Content-Disposition"] = "attachment; filename=%s" % filename
    return response


class StorageViewSet(ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated, HasPermission(permission.STORAGE)]  # type: ignore
    serializer_class = StorageSerializer

    def get_queryset(self):
        """Devices get filtered by account, and optionally by a few URL parameters"""

        # In all cases, we'll only return results for the account of the user
        qs = StorageDevice.objects.filter(account=self.request.user.iaso_profile.account)

        # There are also a few optional URL filters
        filter_status = self.request.query_params.get("status")
        if filter_status is not None:
            qs = qs.filter(status=filter_status)

        filter_reason = self.request.query_params.get("reason")
        if filter_reason is not None:
            qs = qs.filter(status_reason=filter_reason)

        filter_type = self.request.query_params.get("type")
        if filter_type is not None:
            qs = qs.filter(type__in=filter_type.split(","))

        # the search filter works on entity_id or storage (customer-chosen) id
        filter_search = self.request.query_params.get("search")
        if filter_search is not None:
            q = Q(customer_chosen_id__icontains=filter_search)
            try:
                filter_search_int = int(filter_search)
                q = q | Q(entity__id=filter_search_int)
            except ValueError:
                pass

            qs = qs.filter(q)

        return qs

    def list(self, request):
        """
        Endpoint used to list/search devices on the web interface

        GET /api/storages/
        """
        limit_str = request.GET.get("limit", None)
        page_offset = request.GET.get("page", 1)
        order = request.GET.get("order", "updated_at,id").split(",")

        csv_format = request.GET.get("csv", None)
        xlsx_format = request.GET.get("xlsx", None)
        file_export = False

        if csv_format is not None:
            file_export = True
            file_format_export = FileFormatEnum.CSV
        if xlsx_format is not None:
            file_export = True
            file_format_export = FileFormatEnum.XLSX

        queryset = self.get_queryset()
        queryset = queryset.order_by(*order)
        serializer = StorageSerializer

        if file_export:
            return device_generate_export(queryset=queryset, file_format=file_format_export)
        else:  # JSON response for the frontend
            if limit_str is not None:
                limit = int(limit_str)
                page_offset = int(page_offset)
                paginator = Paginator(queryset, limit)
                res = {"count": paginator.count}
                if page_offset > paginator.num_pages:
                    page_offset = paginator.num_pages
                page = paginator.page(page_offset)
                res["results"] = serializer(page.object_list, many=True).data
                res["has_next"] = page.has_next()
                res["has_previous"] = page.has_previous()
                res["page"] = page_offset
                res["pages"] = paginator.num_pages
                res["limit"] = limit
                return Response(res)
            else:
                return Response(StorageSerializer(queryset, many=True).data)

    @action(detail=False, methods=["post"])
    def blacklisted(self, request):
        """
        Endpoint used to blacklist a single device from the web interface

        POST /api/storages/blacklisted/
        """

        # 1. Get data from request/environment
        user = request.user
        body = request.data
        storage_id = body.get("storage_id")
        storage_type = body.get("storage_type")
        storage_status_dict = body.get("storage_status")
        account = user.iaso_profile.account

        # 2. Preprocess submitted data
        try:
            device = StorageDevice.objects.get(customer_chosen_id=storage_id, type=storage_type, account=account)
        except StorageDevice.DoesNotExist:
            device = None

        status_serializer = StorageStatusSerializer(data=storage_status_dict)

        if device is not None and status_serializer.is_valid():
            # 3. Submitted data is valid, we can now proceed
            status_dict = status_serializer.validated_data
            # 3.1 Update device status
            device.change_status(
                new_status=status_dict["status"],
                reason=status_dict.get("status_reason", ""),
                comment=status_dict.get("status_comment", ""),
                performed_by=user,
            )
            return Response({}, status=200)

        else:  # Some parameters were invalid
            return Response({}, status=400)


# This could be rewritten in more idiomatic DRF (serializers, ...). On the other hand, I quite like the explicitness
class StorageLogViewSet(CreateModelMixin, viewsets.GenericViewSet):
    """This ViewSet gives access to the storage log entries"""

    serializer_class = StorageLogSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    @safe_api_import("storageLog", fallback_status=201)
    def create(self, _, request):
        """
        POST /api/mobile/storage/logs [Deprecated] will be removed in the future
        POST /api/mobile/storages/logs

        This will also create a new StorageDevice if the storage_id / storage_type / account combination is not found
        """
        import_storage_logs(request.data, request.user)

        return Response("", status=status.HTTP_201_CREATED)


def import_storage_logs(data, user):
    for log_data in data:
        # We receive an array of logs, we'll process them one by one
        log_id = log_data["id"]

        try:
            StorageLogEntry.objects.get(id=log_id)
            # That log entry already exists, skip it
        except StorageLogEntry.DoesNotExist:
            # New log entry, we continue
            storage_id = log_data["storage_id"]
            storage_type = log_data["storage_type"]
            operation_type = log_data["operation_type"]

            if storage_type not in [c[1] for c in StorageDevice.STORAGE_TYPE_CHOICES]:
                raise ValueError(f"Invalid storage type: {storage_type}")

            if operation_type not in [c[1] for c in StorageLogEntry.OPERATION_TYPE_CHOICES]:
                raise ValueError(f"Invalid operation type: {operation_type}")

            performed_at = timestamp_to_utc_datetime(int(log_data["performed_at"]))

            concerned_instances = Instance.objects.none()
            if "instances" in log_data:
                concerned_instances = Instance.objects.filter(uuid__in=log_data["instances"])

            concerned_orgunit = None
            if "org_unit_id" in log_data and log_data["org_unit_id"] is not None:
                concerned_orgunit = OrgUnit.objects.get(id=log_data["org_unit_id"])

            concerned_entity = None
            entity_id = log_data.get("entity_id") or log_data.get("entity_uuid")
            if entity_id:
                concerned_entity = Entity.objects.get(uuid=entity_id)

            account = user.iaso_profile.account

            # 1. Create the storage device, if needed
            device, _ = StorageDevice.objects.get_or_create(
                account=account, customer_chosen_id=storage_id, type=storage_type
            )

            StorageLogEntry.objects.create_and_update_device(
                log_id=log_id,
                device=device,
                operation_type=operation_type,
                performed_at=performed_at,
                user=user,
                concerned_orgunit=concerned_orgunit,
                concerned_entity=concerned_entity,
                concerned_instances=concerned_instances,
            )


def logs_for_device_generate_export(
    queryset: "QuerySet[StorageLogEntry]", file_format: FileFormatEnum
) -> Union[HttpResponse, StreamingHttpResponse]:
    columns = [
        {"title": "id"},
        {"title": "storage_id"},
        {"title": "storage_type"},
        {"title": "operation_type"},
        {"title": "instances"},
        {"title": "org_unit"},
        {"title": "entity"},
        {"title": "performed_at"},
        {"title": "performed_by"},
        {"title": "status"},
        {"title": "status_reason"},
        {"title": "status_comment"},
    ]

    def get_row(log_entry: StorageLogEntry, **_) -> List[Any]:
        instances_ids_list = ",".join([str(i.id) for i in log_entry.instances.all()])

        performed_at_str = ""
        if log_entry.performed_at is not None:
            performed_at_str = log_entry.performed_at.strftime(EXPORTS_DATETIME_FORMAT)

        return [
            str(log_entry.id),
            log_entry.device.customer_chosen_id,
            log_entry.device.type,
            log_entry.operation_type,
            instances_ids_list,
            log_entry.org_unit_id,
            log_entry.entity_id,
            performed_at_str,
            log_entry.performed_by.username,
            log_entry.status,
            log_entry.status_reason,
            log_entry.status_comment,
        ]

    response: Union[HttpResponse, StreamingHttpResponse]
    filename = "storage_logs"
    if file_format == FileFormatEnum.XLSX:
        filename = filename + ".xlsx"
        response = HttpResponse(
            generate_xlsx("Storage logs", columns, queryset, get_row),
            content_type=CONTENT_TYPE_XLSX,
        )
    elif file_format == FileFormatEnum.CSV:
        filename = filename + ".csv"
        response = StreamingHttpResponse(
            streaming_content=(iter_items(queryset, Echo(), columns, get_row)), content_type=CONTENT_TYPE_CSV
        )

    else:
        # Raise InvalidFileFormat
        pass

    response["Content-Disposition"] = "attachment; filename=%s" % filename
    return response


@api_view()
@permission_classes([IsAuthenticated, HasPermission(permission.STORAGE)])  # type: ignore
def logs_per_device(request, storage_customer_chosen_id: str, storage_type: str):
    """Return a list of log entries for a given device"""

    # 1. Retrieve data from request
    user_account = request.user.iaso_profile.account

    # 1.1 Filters
    org_unit_id = request.GET.get("org_unit_id")
    operation_types_str = request.GET.get("types", None)
    status = request.GET.get("status", None)
    reason = request.GET.get("reason", None)

    # 1.2 Pagination
    limit_str = request.GET.get("limit", None)
    page_offset = request.GET.get("page", 1)

    # 1.3 Ordering
    order = request.GET.get("order", "-performed_at").split(",")

    # 1.4 file export?
    csv_format = request.GET.get("csv", None)
    xlsx_format = request.GET.get("xlsx", None)
    file_export = False
    if csv_format is not None or xlsx_format is not None:
        file_export = True
        file_format_export = FileFormatEnum.CSV if csv_format is not None else FileFormatEnum.XLSX

    performed_at_str = request.GET.get("performed_at", None)

    device_identity_fields = {
        "customer_chosen_id": storage_customer_chosen_id,
        "type": storage_type,
        "account": user_account,
    }

    # We need to filter the log entries early or the paginator (count, ...) will have inconsistent values with the
    # prefetched log entries later
    device = StorageDevice.objects.get(**device_identity_fields)
    log_entries_queryset = StorageLogEntry.objects.filter(device=device).order_by(*order)

    if org_unit_id is not None:
        log_entries_queryset = log_entries_queryset.filter(org_unit_id=org_unit_id)
    if operation_types_str is not None:
        operation_types = operation_types_str.split(",")
        log_entries_queryset = log_entries_queryset.filter(operation_type__in=operation_types)
    if status is not None:
        log_entries_queryset = log_entries_queryset.filter(status=status)
    if reason is not None:
        log_entries_queryset = log_entries_queryset.filter(status_reason=reason)
    if performed_at_str is not None:
        log_entries_queryset = log_entries_queryset.filter(
            performed_at__date=datetime.datetime.strptime(performed_at_str, "%Y-%m-%d").date()
        )

    if not file_export:
        device_with_logs = StorageDevice.objects.prefetch_related(
            Prefetch(
                "log_entries",
                log_entries_queryset,
                to_attr="filtered_log_entries",
            )
        ).get(**device_identity_fields)

        if limit_str:
            # Pagination as requested: each page contains the device metadata + a subset of log entries
            limit = int(limit_str)
            page_offset = int(page_offset)
            paginator = Paginator(log_entries_queryset, limit)
            res = {"count": paginator.count}
            if page_offset > paginator.num_pages:
                page_offset = paginator.num_pages
            page = paginator.page(page_offset)
            res["results"] = StorageSerializerWithPaginatedLogs(  # type: ignore
                device_with_logs, context={"limit": limit, "offset": page.start_index() - 1}
            ).data
            res["has_next"] = page.has_next()
            res["has_previous"] = page.has_previous()
            res["page"] = page_offset
            res["pages"] = paginator.num_pages
            res["limit"] = limit
            return Response(res)
        else:
            return Response(StorageSerializerWithLogs(device_with_logs).data)
    else:
        # File export requested
        return logs_for_device_generate_export(queryset=log_entries_queryset, file_format=file_format_export)


class StorageSerializerForBlacklisted(serializers.ModelSerializer):
    # Since the blacklisted endpoint is open to everyone, we have a specific serializer that expose as little information as possible
    storage_id = serializers.CharField(source="customer_chosen_id")
    storage_type = serializers.CharField(source="type")
    storage_status = StorageStatusSerializerForMobile(source="*")

    class Meta:
        model = StorageDevice
        fields: Tuple[str, ...] = (
            "storage_id",
            "storage_type",
            "storage_status",
        )


class StorageBlacklistedViewSet(ListModelMixin, viewsets.GenericViewSet):
    queryset = StorageDevice.objects.filter(status=StorageDevice.BLACKLISTED)
    serializer_class = StorageSerializerForBlacklisted

    permission_classes = [AllowAny]

    def list(self, request):
        """
        GET /api/mobile/storages/blacklisted
        GET /api/mobile/storage/blacklisted [Deprecated] will be removed in the future

        Returns a list of blacklisted devices
        """
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({"storages": serializer.data})
