import json
import logging
import ntpath
from copy import copy
from time import gmtime, strftime
from typing import Any, Dict, Union, List

import pandas as pd
from django.contrib.auth.models import User
from django.contrib.gis.geos import Point
from django.core.paginator import Paginator
from django.db import connection, transaction
from django.db.models import Count, F, Func, Prefetch, Q, QuerySet
from django.http import HttpResponse, StreamingHttpResponse, Http404
from django.utils.timezone import now
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.request import Request
from rest_framework.response import Response
from typing_extensions import Annotated, TypedDict

import iaso.periods as periods
from hat.api.export_utils import Echo, generate_xlsx, iter_items, timestamp_to_utc_datetime
from hat.audit.models import INSTANCE_API, Modification, log_modification
from hat.common.utils import queryset_iterator
from hat.menupermissions import models as permission
from iaso.api.serializers import OrgUnitSerializer
from iaso.models import (
    Entity,
    Instance,
    InstanceFile,
    InstanceLock,
    InstanceQuerySet,
    OrgUnit,
    OrgUnitChangeRequest,
    Project,
)
from iaso.utils.date_and_time import timestamp_to_datetime
from iaso.utils.file_utils import get_file_type
from .org_units import HasCreateOrgUnitPermission

from ..models.forms import CR_MODE_IF_REFERENCE_FORM
from ..utils.models.common import get_creator_name, check_instance_bulk_gps_push
from . import common
from .comment import UserSerializerForComment
from .common import (
    CONTENT_TYPE_CSV,
    CONTENT_TYPE_XLSX,
    FileFormatEnum,
    TimestampField,
    safe_api_import,
    parse_comma_separated_numeric_values,
)
from .instance_filters import get_form_from_instance_filters, parse_instance_filters

logger = logging.getLogger(__name__)


class InstanceSerializer(serializers.ModelSerializer):
    org_unit = serializers.PrimaryKeyRelatedField(queryset=OrgUnit.objects.all())
    period = serializers.CharField(max_length=9, allow_blank=True)

    class Meta:
        model = Instance
        fields = ["org_unit", "period", "deleted", "last_modified_by"]

    def validate_org_unit(self, value):
        """Check if user has access to this org_unit."""
        # Prevent IA-928: Don't revalidate org unit if it's not modified. As the allowed Type on form or the type
        #  on the org unit can change
        if self.instance and self.instance.org_unit == value:
            return value
        if value.org_unit_type in self.instance.form.org_unit_types.all():
            try:
                return OrgUnit.objects.filter_for_user_and_app_id(self.context["request"].user, None).get(pk=value.pk)
            except OrgUnit.DoesNotExist:
                pass  # that way, if the condition is false, the exception is raised as well
        raise serializers.ValidationError("Org unit type not assigned to this form or not accessible to this user")

    def validate_period(self, value):
        """
        Check if period is of self.instance.form.period_type.
        """

        if periods.detect(value) == self.instance.form.period_type:
            return value
        raise serializers.ValidationError(
            f"Wrong period type, expecting: {self.instance.form.period_type}. Received type: {periods.detect(value)}"
        )


class HasInstancePermission(permissions.BasePermission):
    def has_permission(self, request: Request, view):
        if request.method == "POST":  # to handle anonymous submissions sent by mobile
            return True

        return request.user.is_authenticated and (
            request.user.has_perm(permission.FORMS)
            or request.user.has_perm(permission.SUBMISSIONS)
            or request.user.has_perm(permission.REGISTRY_WRITE)
            or request.user.has_perm(permission.REGISTRY_READ)
        )

    def has_object_permission(self, request: Request, view, obj: Instance):
        # Depends on the Queryset having been filtered previously
        self.has_permission(request, view)
        if request.method in permissions.SAFE_METHODS:
            return True
        # if request.user.has_perm("menupermission.iaso_update_submission") and obj.can_user_modify(request.user):
        if obj.can_user_modify(request.user):
            return True
        return False


class HasInstanceBulkPermission(permissions.BasePermission):
    """
    Designed for POST endpoints that are not designed to receive new submissions.
    """

    def has_permission(self, request: Request, view):
        return request.user.is_authenticated and (
            request.user.has_perm(permission.FORMS)
            or request.user.has_perm(permission.SUBMISSIONS)
            or request.user.has_perm(permission.REGISTRY_WRITE)
            or request.user.has_perm(permission.REGISTRY_READ)
        )


class InstanceFileSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    instance_id = serializers.IntegerField()
    file = serializers.FileField(use_url=True)
    created_at = TimestampField(read_only=True)
    file_type = serializers.SerializerMethodField()

    def get_file_type(self, obj):
        return get_file_type(obj.file)


class OrgUnitNestedSerializer(OrgUnitSerializer):
    class Meta:
        model = OrgUnit

        fields = [
            "id",
            "name",
        ]


# For readonly use
class InstanceLockSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstanceLock
        fields = ["id", "top_org_unit", "locked_by", "locked_at", "unlocked_by", "locked_by"]
        read_only_fields = ["locked_at", "locked_by"]

    # TODO: can we use the generic UserSerializer to keeps things less interleaved?
    locked_by = UserSerializerForComment(read_only=True)
    unlocked_by = UserSerializerForComment(read_only=True)
    top_org_unit = OrgUnitNestedSerializer(read_only=True)


class UnlockSerializer(serializers.Serializer):
    lock = serializers.PrimaryKeyRelatedField(queryset=InstanceLock.objects.all())
    # we will  check that the user can access from the directly in remove_lock()


class LockAnnotation(TypedDict):
    count_lock_applying_to_user: int
    count_active_lock: int


class InstancesViewSet(viewsets.ViewSet):
    f"""Instances API

    Posting instances can be done anonymously (if the project allows it), all other methods are restricted
    to authenticated users having the "{permission.FORMS}" permission.

    GET /api/instances/
    GET /api/instances/<id>
    DELETE /api/instances/<id>
    POST /api/instances/
    PATCH /api/instances/<id>
    """

    permission_classes = [HasInstancePermission]

    def get_queryset(self):
        request = self.request
        queryset: InstanceQuerySet = Instance.objects.order_by("-id")
        queryset = queryset.filter_for_user(request.user)
        return queryset

    @action(["GET"], detail=False)
    def attachments(self, request):
        instances = self.get_queryset()
        filters = parse_instance_filters(request.GET)
        instances = instances.for_filters(**filters)
        queryset = InstanceFile.objects.filter(instance__in=instances).annotate(
            file_extension=Func(F("file"), function="LOWER", template="SUBSTRING(%(expressions)s, '\.([^\.]+)$')")
        )

        image_only = request.GET.get("image_only", "false").lower() == "true"
        if image_only:
            image_extensions = ["jpg", "jpeg", "png", "gif", "bmp", "tiff", "webp"]
            queryset = queryset.filter(file_extension__in=image_extensions)

        paginator = common.Paginator()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = InstanceFileSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = InstanceFileSerializer(queryset, many=True)
        return Response(serializer.data)

    @staticmethod
    def list_file_export(filters: Dict[str, Any], queryset: "QuerySet[Instance]", file_format: FileFormatEnum):
        """WIP: Helper function to divide the huge list method"""
        columns = [
            {"title": "ID du formulaire", "width": 20},
            {"title": "Version du formulaire", "width": 20},
            {"title": "Export id", "width": 20},
            {"title": "Latitude", "width": 40},
            {"title": "Longitude", "width": 20},
            {"title": "Altitude", "width": 20},
            {"title": "Précision", "width": 20},
            {"title": "Période", "width": 20},
            {"title": "Date de création", "width": 20},
            {"title": "Date de modification", "width": 20},
            {"title": "Créé par", "width": 20},
            {"title": "Status", "width": 20},
            {"title": "Entité", "width": 20},
            {"title": "Org unit", "width": 20},
            {"title": "Org unit id", "width": 20},
            {"title": "Référence externe", "width": 20},
            {"title": "parent1", "width": 20},
            {"title": "parent2", "width": 20},
            {"title": "parent3", "width": 20},
            {"title": "parent4", "width": 20},
        ]

        filename = "instances"

        form = get_form_from_instance_filters(filters)

        if form:
            filename = "%s-%s" % (filename, form.id)
            if form.correlatable:
                columns.append({"title": "correlation id", "width": 20})
        else:
            return Response({"error": "There is no form"}, status=status.HTTP_400_BAD_REQUEST)

        sub_columns = ["" for __ in columns]
        latest_form_version = form.latest_version
        questions_by_name = latest_form_version.questions_by_name() if latest_form_version else {}
        if form and latest_form_version:
            file_content_template = questions_by_name
            for title in file_content_template:
                # some form have dict as label to support MuliLang. So convert to String
                # e.g. Vaccine Stock Monitoring {'French': 'fin', 'English': 'end'}
                label = file_content_template.get(title, {}).get("label", "")
                if isinstance(label, dict):
                    label = str(label)
                sub_columns.append(label)
                columns.append({"title": title, "width": 50})
        else:
            file_content_template = queryset.first().as_dict()["file_content"]  # type: ignore
            for title in file_content_template:
                columns.append({"title": title, "width": 50})
                sub_columns.append(questions_by_name.get(title, {}).get("label", ""))

        filename = "%s-%s" % (filename, strftime("%Y-%m-%d-%H-%M", gmtime()))

        def get_row(instance, **kwargs):
            created_at_timestamp = instance.source_created_at_with_fallback.timestamp()
            updated_at_timestamp = instance.source_updated_at_with_fallback.timestamp()
            org_unit = instance.org_unit
            file_content = instance.get_and_save_json_of_xml()

            instance_values = [
                instance.id,
                file_content.get("_version") if file_content else None,
                instance.export_id,
                instance.location.y if instance.location else None,
                instance.location.x if instance.location else None,
                instance.location.z if instance.location else None,
                instance.accuracy,
                instance.period,
                timestamp_to_datetime(created_at_timestamp),
                timestamp_to_datetime(updated_at_timestamp),
                get_creator_name(instance.created_by) if instance.created_by else None,
                instance.status,
                # Special format for UUID to stay consistent with other UUIDs coming from file_content_template
                f"uuid:{instance.entity.uuid}" if instance.entity else None,
                instance.org_unit.name,
                instance.org_unit.id,
                instance.org_unit.source_ref,
            ]

            parent = org_unit.parent
            for i in range(4):
                if parent:
                    instance_values.append(parent.name)
                    parent = parent.parent
                else:
                    instance_values.append("")
            if instance.form.correlatable:
                instance_values.append(instance.correlation_id)

            for k in file_content_template:
                v = file_content.get(k, None)
                if type(v) is list:
                    instance_values.append(json.dumps(v))
                else:
                    instance_values.append(v)
            return instance_values

        response: Union[HttpResponse, StreamingHttpResponse]

        queryset = queryset.prefetch_related("created_by", "entity", "form_version__form")
        queryset = queryset.prefetch_related(
            Prefetch("org_unit", queryset=OrgUnit.objects.only("name", "parent_id", "source_ref"))
        )
        queryset = queryset.prefetch_related(
            Prefetch(
                "org_unit__parent",
                queryset=OrgUnit.objects.only("name", "parent_id", "source_ref"),
            )
        )
        queryset = queryset.prefetch_related(
            Prefetch(
                "org_unit__parent__parent",
                queryset=OrgUnit.objects.only("name", "parent_id", "source_ref"),
            )
        )
        queryset = queryset.prefetch_related(
            Prefetch(
                "org_unit__parent__parent__parent",
                queryset=OrgUnit.objects.only("name", "parent_id", "source_ref"),
            )
        )
        queryset = queryset.prefetch_related(
            Prefetch(
                "org_unit__parent__parent__parent__parent",
                queryset=OrgUnit.objects.only("name", "parent_id", "source_ref"),
            )
        )

        if file_format == FileFormatEnum.XLSX:
            filename = filename + ".xlsx"
            response = HttpResponse(
                generate_xlsx("Forms", columns, queryset_iterator(queryset, 100), get_row, sub_columns),
                content_type=CONTENT_TYPE_XLSX,
            )
        elif file_format == FileFormatEnum.CSV:
            filename = filename + ".csv"
            response = StreamingHttpResponse(
                streaming_content=(iter_items(queryset, Echo(), columns, get_row)), content_type=CONTENT_TYPE_CSV
            )
        else:
            raise ValueError(f"Unknown file format requested: {file_format}")

        response["Content-Disposition"] = "attachment; filename=%s" % filename
        return response

    def list(self, request):
        """List instances: this endpoint is used for both searches and file exports"""

        # 1. Get data out of the request
        limit = request.GET.get("limit", None)
        as_small_dict = request.GET.get("asSmallDict", None)
        page_offset = request.GET.get("page", 1)
        orders = request.GET.get("order", "updated_at").split(",")
        csv_format = request.GET.get("csv", None)
        xlsx_format = request.GET.get("xlsx", None)
        filters = parse_instance_filters(request.GET)
        org_unit_status = request.GET.get("org_unit_status", None)  # "NEW", "VALID", "REJECTED"
        with_descriptor = request.GET.get("with_descriptor", "false")

        file_export = False
        if csv_format is not None or xlsx_format is not None:
            file_export = True
            file_format_export = FileFormatEnum.CSV if csv_format is not None else FileFormatEnum.XLSX

        # 2. Prepare queryset (common part between searches and exports)
        queryset = self.get_queryset()
        queryset = queryset.exclude(file="").exclude(device__test_device=True)
        queryset = queryset.prefetch_related("form")
        queryset = queryset.prefetch_related("created_by")
        queryset = queryset.for_filters(**filters)
        queryset = queryset.order_by(*orders)
        # IA-1023 = allow to sort instances by form version

        # TODO: this function would deserve some more thorough refactor, see the discussion at
        #  https://bluesquare.atlassian.net/browse/IA-1547. Some things were cleaned already, but it would make sense
        #  to change it so:
        #  - 1) the same queryset is prepared at the beginning of the function, then used in all cases (searches,
        #       exports, paginated or not, as small dict or not)
        #  - 2) the limit and asSmallDict parameters are independent from each other (the consumer can choose to use
        #       one, both or None and get predictable results)
        if org_unit_status:
            queryset = queryset.filter(org_unit__validation_status=org_unit_status)

        if not file_export:
            queryset = queryset.prefetch_related("org_unit__reference_instances")
            queryset = queryset.prefetch_related("org_unit__org_unit_type__reference_forms")
            queryset = queryset.prefetch_related("org_unit__version__data_source")
            queryset = queryset.prefetch_related("project")
            if limit:
                limit = int(limit)
                page_offset = int(page_offset)

                queryset = queryset.with_lock_info(user=request.user)

                paginator = Paginator(queryset, limit)
                res = {"count": paginator.count}
                if page_offset > paginator.num_pages:
                    page_offset = paginator.num_pages
                page = paginator.page(page_offset)

                def as_dict_formatter(instance: Annotated[Instance, LockAnnotation]) -> Dict:
                    d = instance.as_dict_with_descriptor() if with_descriptor == "true" else instance.as_dict()
                    d["can_user_modify"] = instance.count_lock_applying_to_user == 0
                    d["is_locked"] = instance.count_active_lock > 0
                    d["is_instance_of_reference_form"] = instance.is_instance_of_reference_form
                    d["is_reference_instance"] = instance.is_reference_instance
                    return d

                res["instances"] = map(as_dict_formatter, page.object_list)
                res["has_next"] = page.has_next()
                res["has_previous"] = page.has_previous()
                res["page"] = page_offset
                res["pages"] = paginator.num_pages
                res["limit"] = limit

                return Response(res)
            elif as_small_dict:
                # TODO: apparently, this branch is not used by the frontend nor the mobile app
                queryset = (
                    queryset.annotate(instancefile_count=Count("instancefile"))
                    .filter(Q(location__isnull=False) | Q(instancefile_count__gt=0))
                    .prefetch_related("instancefile_set")
                    .prefetch_related("device")
                    .defer("json")
                )
                return Response([instance.as_small_dict() for instance in queryset])
            else:
                return Response(
                    {
                        "instances": [
                            instance.as_dict_with_descriptor() if with_descriptor == "true" else instance.as_dict()
                            for instance in queryset
                        ]
                    }
                )
        else:  # This is a CSV/XLSX file export
            return self.list_file_export(filters=filters, queryset=queryset, file_format=file_format_export)

    @action(detail=True, methods=["POST"])
    def add_lock(self, request, pk):
        # would use get_object usually, but we are not in a ModelViewSet
        instance = get_object_or_404(self.get_queryset(), pk=pk)
        self.check_object_permissions(request, instance)
        new_lock = self.add_lock_instance(instance, request.user)
        return Response({"status": "lock added", "lock_id": new_lock.id})

    # @action(detail=False, methods=["POST"], serializer_class = UnlockSerializer)
    @action(detail=False, methods=["POST"])
    def unlock_lock(self, request):
        serializer = UnlockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        lock = serializer.validated_data["lock"]
        self.check_object_permissions(request, lock.instance)
        self._unlock_lock(request.user, lock)
        return Response({"status": "lock removed", "lock_id": lock.id})

    def add_lock_instance(self, instance: Instance, user):
        #  OrgUnit in the user org unit that's the highest
        user_orgunits = user.iaso_profile.org_units
        # user orgunit that contain the instance's orgunit and is the highest level.
        if not user_orgunits.exists():
            # user is not restricted to any orgunit, use the root that contain the instance
            # FIXME: what if instance.org_unit is None?
            top_level = OrgUnit.objects.filter(path__ancestors=instance.org_unit.path).order_by("path__depth").first()  # type: ignore
        else:
            # FIXME: what if instance.org_unit is None?
            top_level = user_orgunits.filter(path__ancestors=instance.org_unit.path).order_by("path__depth").first()  # type: ignore
        assert top_level, "No intersection found"  # should not happen

        lock = InstanceLock.objects.create(locked_by=user, top_org_unit=top_level, instance=instance)
        return lock

    def _unlock_lock(self, user: User, lock):
        # Can user modify this instance

        # is lock actually locked, should not happen in the ui normally
        if lock.unlocked_by is not None:
            raise serializers.ValidationError({"lock": "Lock already unlocked"})

        lock.unlocked_by = user
        lock.unlocked_at = now()
        lock.save()

    @safe_api_import("instance")
    def create(self, _, request):
        import_data(request.data, request.user, request.query_params.get("app_id"))

        return Response({"res": "ok"})

    def retrieve(self, request, pk=None):
        queryset = (
            self.get_queryset()
            .prefetch_related(
                "instancelock_set",
                "instancelock_set__top_org_unit",
                "instancelock_set__locked_by",
                "instancelock_set__unlocked_by",
                "org_unit__reference_instances",
                "org_unit__org_unit_type__reference_forms",
            )
            .with_status()
        )
        instance: Instance = get_object_or_404(queryset, pk=pk)
        self.check_object_permissions(request, instance)
        all_instance_locks = instance.instancelock_set.all()

        response = instance.as_full_model(with_entity=True)

        # Logs(history) of all instance locks
        response["instance_locks"] = InstanceLockSerializer(all_instance_locks, many=True).data
        # To display the Lock or unlock icon when the use has access to the two actions
        response["can_user_modify"] = instance.can_user_modify(request.user)
        # To display either the "unlock" or the "lock" icon depending on if the instance is already lock or not
        response["is_locked"] = any(lock.unlocked_by is None for lock in all_instance_locks)

        response["is_instance_of_reference_form"] = instance.is_instance_of_reference_form
        response["is_reference_instance"] = instance.is_reference_instance

        return Response(response)

    def delete(self, request, pk=None):
        original = get_object_or_404(self.get_queryset(), pk=pk)
        instance = get_object_or_404(self.get_queryset(), pk=pk)
        self.check_object_permissions(request, instance)
        instance.soft_delete()
        log_modification(original, instance, INSTANCE_API, user=request.user)
        return Response(instance.as_full_model())

    def patch(self, request, pk=None):
        original = get_object_or_404(self.get_queryset(), pk=pk)
        instance = get_object_or_404(self.get_queryset(), pk=pk)
        self.check_object_permissions(request, instance)
        data = {
            **request.data,
            "last_modified_by": request.user.id,
        }
        instance_serializer = InstanceSerializer(instance, data=data, partial=True, context={"request": self.request})
        instance_serializer.is_valid(raise_exception=True)
        access_ou = OrgUnit.objects.filter_for_user_and_app_id(request.user, None)
        data_org_unit = request.data.get("org_unit", None)

        if instance.org_unit not in access_ou:
            raise serializers.ValidationError({"error": "You don't have the permission to modify this instance."})

        # If the org unit change but the instance was marked as the reference_instance for this org unit,
        # remove the reference as reference instance
        # FIXME we should log the modification on org unit
        if (original.org_unit_id != data_org_unit) and original.is_reference_instance:
            previous_orgunit = original.org_unit
            original.unflag_reference_instance(previous_orgunit)
            previous_orgunit.save()
        instance_serializer.save()

        instance.last_modified_by = request.user
        instance.save()
        log_modification(original, instance, INSTANCE_API, user=request.user)
        return Response(instance.as_full_model())

    @action(detail=False, methods=["POST"], permission_classes=[permissions.IsAuthenticated, HasInstancePermission])
    def bulkdelete(self, request):
        select_all = request.data.get("select_all", None)
        selected_ids = request.data.get("selected_ids", None)
        unselected_ids = request.data.get("unselected_ids", None)
        is_deletion = request.data.get("is_deletion", True)

        filters = parse_instance_filters(request.data)
        instances_query = self.get_queryset()
        instances_query = instances_query.prefetch_related("form")
        instances_query = instances_query.exclude(file="").exclude(device__test_device=True)
        instances_query = instances_query.for_filters(**filters)
        if not select_all:
            instances_query = instances_query.filter(pk__in=selected_ids)
        else:
            instances_query = instances_query.exclude(pk__in=unselected_ids)
        for instance in instances_query:
            self.check_object_permissions(request, instance)

        try:
            with transaction.atomic():
                for instance in instances_query.iterator():
                    original = copy(instance)
                    if is_deletion == True:
                        instance.soft_delete()
                    else:
                        instance.restore()
                    log_modification(original, instance, INSTANCE_API, user=request.user)

        except Exception as e:
            print(f"Error : {e}")
            return Response(
                {"result": "A problem happened while deleting instances"}, status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {
                "result": "success",
            },
            status=201,
        )

    @action(
        detail=False,
        methods=["GET"],
        permission_classes=[permissions.IsAuthenticated, HasInstanceBulkPermission, HasCreateOrgUnitPermission],
    )
    def check_bulk_gps_push(self, request):
        # first, let's parse all parameters received from the URL
        select_all, selected_ids, unselected_ids = self._parse_check_bulk_gps_push_parameters(request.GET)

        # then, let's make sure that each ID actually exists and that the user has access to it
        instances_query = self.get_queryset()
        if instances_query.filter(pk__in=selected_ids).count() != len(selected_ids):
            raise Http404
        if instances_query.filter(pk__in=unselected_ids).count() != len(unselected_ids):
            raise Http404

        # let's filter everything
        filters = parse_instance_filters(request.GET)
        instances_query = instances_query.select_related("org_unit")
        instances_query = instances_query.exclude(file="").exclude(device__test_device=True)
        instances_query = instances_query.for_filters(**filters)

        if not select_all:
            instances_query = instances_query.filter(pk__in=selected_ids)
        else:
            instances_query = instances_query.exclude(pk__in=unselected_ids)

        success, errors, warnings = check_instance_bulk_gps_push(instances_query)

        if not success:
            errors["result"] = "errors"
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        if warnings:
            warnings["result"] = "warnings"
            return Response(warnings, status=status.HTTP_200_OK)

        return Response(
            {
                "result": "success",
            },
            status=status.HTTP_200_OK,
        )

    def _parse_check_bulk_gps_push_parameters(self, query_parameters):
        raw_select_all = query_parameters.get("select_all", True)
        select_all = raw_select_all not in ["false", "False", "0", 0, False]

        raw_selected_ids = query_parameters.get("selected_ids", None)
        if raw_selected_ids:
            selected_ids = parse_comma_separated_numeric_values(raw_selected_ids, "selected_ids")
        else:
            selected_ids = []

        raw_unselected_ids = query_parameters.get("unselected_ids", None)
        if raw_unselected_ids:
            unselected_ids = parse_comma_separated_numeric_values(raw_unselected_ids, "unselected_ids")
        else:
            unselected_ids = []

        return select_all, selected_ids, unselected_ids

    QUERY = """
    select DATE_TRUNC('month', COALESCE(iaso_instance.source_created_at, iaso_instance.created_at)) as month,
           (select name from iaso_form where id = iaso_instance.form_id) as form_name,
           iaso_instance.form_id,
           count(*)                        as value
    from iaso_instance
    left join iaso_form on (iaso_form.id = iaso_instance.form_id)
    where COALESCE(iaso_instance.source_created_at, iaso_instance.created_at) > '2019-01-01'
      and project_id = ANY (%s)
      and iaso_instance.form_id is not null
      and iaso_instance.deleted =  false
      and iaso_form.deleted_at is null
    group by DATE_TRUNC('month', COALESCE(iaso_instance.source_created_at, iaso_instance.created_at)), iaso_instance.form_id
    order by DATE_TRUNC('month', COALESCE(iaso_instance.source_created_at, iaso_instance.created_at))"""

    @action(detail=False)
    def stats(self, request):
        project_ids_param = request.GET.get("project_ids", None)
        projects = request.user.iaso_profile.account.project_set.all()

        if project_ids_param:
            project_ids_array = project_ids_param.split(",")
            projects = projects.filter(id__in=project_ids_array)

        projects_ids = list(projects.values_list("id", flat=True))

        df = pd.read_sql_query(self.QUERY, connection, params=[projects_ids])
        # Keep the form name
        names = df[["form_id", "form_name"]].drop_duplicates().set_index("form_id")
        names_dict = names["form_name"].to_dict()

        # Pivot on the form_id because there might be form with duplicate name
        df = df.pivot(index="month", columns="form_id", values="value")
        if not df.empty:
            df.index = df.index.to_period("M")
            df = df.sort_index()
            df = df.reindex(pd.period_range(df.index[0], df.index[-1], freq="M"))
            df["name"] = df.index.astype(str)  # Name column is the month
            df = df.rename(columns=names_dict)
        r = df.to_json(orient="table")
        return HttpResponse(r, content_type="application/json")

    @action(detail=False)
    def stats_sum(self, request):
        project_ids_param = request.GET.get("project_ids", None)
        projects = request.user.iaso_profile.account.project_set.all()

        if project_ids_param:
            project_ids_array = project_ids_param.split(",")
            projects = projects.filter(id__in=project_ids_array)

        projects_ids = list(projects.values_list("id", flat=True))
        QUERY = """
        select DATE_TRUNC('day', COALESCE(iaso_instance.source_created_at, iaso_instance.created_at)) as period,
        count(*)                        as value
        from iaso_instance
        left join iaso_form on (iaso_form.id = iaso_instance.form_id)
        where COALESCE(iaso_instance.source_created_at, iaso_instance.created_at) > now() - interval '2700 days'
        and project_id = ANY (%s)
        and iaso_instance.deleted = false
        and iaso_form.deleted_at is null
        group by DATE_TRUNC('day', COALESCE(iaso_instance.source_created_at, iaso_instance.created_at))
        order by 1"""
        df = pd.read_sql_query(QUERY, connection, params=[projects_ids])
        df["total"] = df["value"].cumsum()
        df["name"] = df["period"].apply(lambda x: x.strftime("%Y-%m-%d"))
        r = df.to_json(orient="table")
        return HttpResponse(r, content_type="application/json")

    @action(detail=True, methods=["get"], url_path="instance_logs/(?P<logId>[^/.]+)")
    def instance_logs(self, request, pk=None, logId=None):
        """
        GET /api/instances/<pk>/instance_logs/<logId>/
        """
        instance = get_object_or_404(
            Instance.objects.filter(pk=pk).prefetch_related(
                Prefetch(
                    "instancefile_set",
                    queryset=InstanceFile.objects.filter(deleted=False).only("file"),
                    to_attr="filtered_files",
                )
            )
        )
        log = get_object_or_404(Modification, pk=logId)
        log_dict = log.as_dict()
        possible_fields = (
            instance.form_version.possible_fields
            if instance.form_version and instance.form_version.possible_fields
            else []
        )
        log_dict["files"] = [f.file.url if f.file else None for f in instance.filtered_files]
        log_dict["possible_fields"] = possible_fields
        return Response(log_dict)


def import_data(instances, user, app_id):
    project = Project.objects.get_for_user_and_app_id(user, app_id)

    for instance_data in instances:
        uuid = instance_data.get("id", None)

        if Instance.objects.filter(uuid=uuid).exists():
            continue

        # Get or create instance based on file_name - this "get or create" logic is important:
        # it is possible (although it won't happen often) that the instance has already been created by the
        # POST /sync/ endpoint.
        file_name = ntpath.basename(instance_data.get("file", None))
        instance, _ = Instance.objects.get_or_create(file_name=file_name)

        instance.uuid = uuid
        instance.project = project
        instance.name = instance_data.get("name", None)
        instance.period = instance_data.get("period", None)
        instance.accuracy = instance_data.get("accuracy", None)

        tentative_org_unit_id = instance_data.get("orgUnitId", None)
        if str(tentative_org_unit_id).isdigit():
            instance.org_unit_id = tentative_org_unit_id
        else:
            org_unit = OrgUnit.objects.get(uuid=tentative_org_unit_id)
            instance.org_unit = org_unit

        instance.form_id = instance_data.get("formId")

        # TODO: check that planning_id is valid
        instance.planning_id = instance_data.get("planningId", None)
        entity_uuid = instance_data.get("entityUuid", None)
        entity_type_id = instance_data.get("entityTypeId", None)
        if entity_uuid and entity_type_id:
            # In case of duplicate UUIDs in the database, only allow 1 non-deleted one.
            # If a non-deleted entity was found, ignore potential duplicates.
            filters = {
                "uuid": entity_uuid,
                "entity_type_id": entity_type_id,
                "account": project.account,
            }
            existing_entities = list(Entity.objects_include_deleted.filter(**filters))

            if len(existing_entities) == 0:
                entity = Entity.objects.create(**filters)
            elif len(existing_entities) == 1:
                entity = existing_entities[0]
            else:
                # In case of duplicates, try to take the "best" one. Best one would
                # be one that's not deleted and that has valid attributes with a
                # file attached. We first assign the first one to avoid having None.
                # If there are multiple non-deleted entities, we send a Sentry,
                # but don't break the upload.
                if len([e for e in existing_entities if e.deleted_at is None]) > 1:
                    logger.exception(
                        f"Multiple non-deleted entities for UUID {entity_uuid}, entity_type_id {entity_type_id}"
                    )

                entity = sorted(existing_entities, key=_entity_correctness_score, reverse=True)[0]

            if entity.deleted_at:
                logger.info(
                    f"Entity %s is soft-deleted for instance %s %s",
                    entity.uuid,
                    instance.uuid,
                    instance.name,
                )
                if entity.merged_to:
                    active_entity = entity.merged_to
                    while active_entity.deleted_at and active_entity.merged_to:
                        active_entity = active_entity.merged_to
                    logger.info(
                        f"Adding new instance %s %s to merged entity %s",
                        instance.uuid,
                        instance.name,
                        active_entity.uuid,
                    )
                    entity = active_entity
                else:
                    instance.deleted = True

            instance.entity = entity

            # If instance's form is the same as the type reference form, set the instance as reference_instance
            if entity.entity_type.reference_form == instance.form:
                entity.attributes = instance
                entity.save()

        created_at_ts = instance_data.get("created_at", None)
        if created_at_ts:
            instance.source_created_at = timestamp_to_utc_datetime(int(created_at_ts))

        updated_at_ts = instance_data.get("updated_at", None)
        if updated_at_ts:
            instance.source_updated_at = timestamp_to_utc_datetime(int(updated_at_ts))

        latitude = instance_data.get("latitude", None)
        longitude = instance_data.get("longitude", None)
        if latitude and longitude:
            altitude = instance_data.get("altitude", 0)
            instance.location = Point(x=longitude, y=latitude, z=altitude, srid=4326)

        instance.save()

        if instance.form.change_request_mode == CR_MODE_IF_REFERENCE_FORM:
            if instance.form in instance.org_unit.org_unit_type.reference_forms.all():
                oucr = OrgUnitChangeRequest()
                oucr.org_unit = instance.org_unit
                if user and not user.is_anonymous:
                    oucr.created_by = user
                previous_reference_instances = list(instance.org_unit.reference_instances.all())
                new_reference_instances = list(filter(lambda i: i.form != instance.form, previous_reference_instances))
                new_reference_instances.append(instance)
                oucr.save()
                oucr.new_reference_instances.set(new_reference_instances)
                oucr.requested_fields = ["new_reference_instances"]
                oucr.save()


def _entity_correctness_score(entity):
    """
    A small function that allows sorting entities to pick the right one for
    incoming data in case of duplicates. A deleted one is always less than an active
    one, etc.
    """
    score = 0
    if not entity.deleted_at:
        score += 100
    if entity.attributes:
        score += 10
    if entity.attributes and entity.attributes.file and not entity.attributes.file == "":
        score += 1

    return score
