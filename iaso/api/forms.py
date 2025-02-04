import typing
from copy import copy
from datetime import timedelta
from xml.sax.saxutils import escape

from django.db.models import BooleanField, Case, Count, Max, Q, When
from django.http import HttpResponse, StreamingHttpResponse
from django.utils.dateparse import parse_date
from rest_framework import permissions, serializers, status
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.request import Request

from hat.api.export_utils import Echo, generate_xlsx, iter_items
from hat.audit.models import FORM_API, log_modification
from hat.menupermissions import models as permission
from iaso.models import Form, FormPredefinedFilter, OrgUnit, OrgUnitType, Project
from iaso.utils.date_and_time import timestamp_to_datetime

from .common import CONTENT_TYPE_CSV, CONTENT_TYPE_XLSX, DynamicFieldsModelSerializer, ModelViewSet, TimestampField
from .enketo import public_url_for_enketo
from .projects import ProjectSerializer
from ..permissions import IsAuthenticatedOrReadOnlyWhenNoAuthenticationRequired


class HasFormPermission(IsAuthenticatedOrReadOnlyWhenNoAuthenticationRequired):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return super().has_permission(request, view)

        return request.user.is_authenticated and request.user.has_perm(permission.FORMS)

    def has_object_permission(self, request, view, obj):
        if not self.has_permission(request, view):
            return False
        return (
            Form.objects_include_deleted.filter_for_user_and_app_id(request.user, request.query_params.get("app_id"))
            .filter(id=obj.id)
            .exists()
        )


class FormPredefinedFilterSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormPredefinedFilter
        fields = ["id", "name", "short_name", "json_logic", "created_at", "updated_at"]

    created_at = TimestampField(read_only=True)
    updated_at = TimestampField(read_only=True)


class FormSerializer(DynamicFieldsModelSerializer):
    class Meta:
        model = Form
        default_fields = [
            "id",
            "name",
            "form_id",
            "device_field",
            "location_field",
            "org_unit_types",
            "org_unit_type_ids",
            "projects",
            "project_ids",
            "period_type",
            "single_per_period",
            "periods_before_allowed",
            "periods_after_allowed",
            "latest_form_version",
            "instances_count",
            "instance_updated_at",
            "created_at",
            "updated_at",
            "deleted_at",
            "derived",
            "fields",
            "label_keys",
            "reference_form_of_org_unit_types",
            "legend_threshold",
            "change_request_mode",
            "has_mappings",
        ]
        fields = [
            "id",
            "name",
            "form_id",
            "device_field",
            "location_field",
            "org_unit_types",
            "org_unit_type_ids",
            "projects",
            "project_ids",
            "period_type",
            "single_per_period",
            "periods_before_allowed",
            "periods_after_allowed",
            "latest_form_version",
            "instances_count",
            "instance_updated_at",
            "created_at",
            "updated_at",
            "deleted_at",
            "derived",
            "possible_fields",
            "label_keys",
            "predefined_filters",
            "has_attachments",
            "reference_form_of_org_unit_types",
            "legend_threshold",
            "change_request_mode",
            "has_mappings",
            "possible_fields_with_latest_version",
        ]
        read_only_fields = [
            "id",
            "form_id",
            "org_unit_types",
            "projects",
            "instances_count",
            "instance_updated_at",
            "created_at",
            "updated_at",
            "possible_fields",
            "fields",
            "has_attachments",
            "reference_form_of_org_unit_types",
            "has_mappings",
        ]

    org_unit_types = serializers.SerializerMethodField()
    org_unit_type_ids = serializers.PrimaryKeyRelatedField(
        source="org_unit_types", many=True, allow_empty=True, queryset=OrgUnitType.objects.all()
    )
    projects = ProjectSerializer(read_only=True, many=True)
    project_ids = serializers.PrimaryKeyRelatedField(
        source="projects", many=True, allow_empty=False, queryset=Project.objects.all()
    )
    latest_form_version = serializers.SerializerMethodField()  # TODO: use FormSerializer
    instances_count = serializers.IntegerField(read_only=True)
    instance_updated_at = TimestampField(read_only=True)
    predefined_filters = FormPredefinedFilterSerializer(many=True)
    created_at = TimestampField(read_only=True)
    updated_at = TimestampField(read_only=True)
    deleted_at = TimestampField(allow_null=True, required=False)
    has_attachments = serializers.SerializerMethodField()
    reference_form_of_org_unit_types = serializers.SerializerMethodField()
    has_mappings = serializers.BooleanField(read_only=True)
    possible_fields_with_latest_version = serializers.SerializerMethodField()

    @staticmethod
    def get_latest_form_version(obj: Form):
        return obj.latest_version.as_dict() if obj.latest_version is not None else None

    @staticmethod
    def get_org_unit_types(obj: Form):
        return [t.as_dict() for t in obj.org_unit_types.all()]

    @staticmethod
    def get_reference_form_of_org_unit_types(obj: Form):
        return [org_unit.as_dict() for org_unit in obj.reference_of_org_unit_types.all()]

    @staticmethod
    def get_has_attachments(obj: Form):
        return len(obj.attachments.all()) > 0

    @staticmethod
    def get_possible_fields_with_latest_version(obj: Form):
        latest_version = obj.latest_version
        if not latest_version:
            return obj.possible_fields

        # Get the field names from the latest version
        latest_version_fields = set(question["name"] for question in latest_version.questions_by_name().values())

        # Add a flag to each possible field indicating if it's part of the latest version
        return [{**field, "is_latest": field["name"] in latest_version_fields} for field in obj.possible_fields]

    def validate(self, data: typing.Mapping):
        # validate projects (access check)
        if "projects" in data:
            for project in data["projects"]:
                if self.context["request"].user.iaso_profile.account != project.account:
                    raise serializers.ValidationError({"project_ids": "Invalid project ids"})

            # validate org_unit_types against projects
            allowed_org_unit_types = [ut for p in data["projects"] for ut in p.unit_types.all()]
            if len(set(data["org_unit_types"]) - set(allowed_org_unit_types)) > 0:
                raise serializers.ValidationError({"org_unit_type_ids": "Invalid org unit type ids"})

        # If the period type is None, some period-specific fields must have specific values
        if "period_type" in data:
            tracker_errors = {}
            if data["period_type"] is None:
                if data["periods_before_allowed"] != 0:
                    tracker_errors["periods_before_allowed"] = "Should be 0 when period type is not specified"
                if data["periods_after_allowed"] != 0:
                    tracker_errors["periods_after_allowed"] = "Should be 0 when period type is not specified"
            else:
                before = data.get("periods_before_allowed", 0)
                after = data.get("periods_after_allowed", 0)
                if before + after < 1:
                    tracker_errors[
                        "periods_allowed"
                    ] = "periods_before_allowed + periods_after_allowed should be greater than or equal to 1"
            if tracker_errors:
                raise serializers.ValidationError(tracker_errors)
        return data

    def update(self, form, validated_data):
        original = copy(form)
        form = super(FormSerializer, self).update(form, validated_data)
        log_modification(original, form, FORM_API, user=self.context["request"].user)
        return form

    def create(self, validated_data):
        form = super(FormSerializer, self).create(validated_data)
        log_modification(None, form, FORM_API, user=self.context["request"].user)
        return form


class FormsViewSet(ModelViewSet):
    f"""Forms API

    Read-only methods are accessible to anonymous users. All other actions are restricted to authenticated users
    having the "{permission.FORMS}"  permission.

    GET /api/forms/
    GET /api/forms/<id>
    POST /api/forms/
    PUT /api/forms/<id>
    PATCH /api/forms/<id>
    DELETE /api/forms/<id>
    """

    permission_classes = [HasFormPermission]
    serializer_class = FormSerializer
    results_key = "forms"

    EXPORT_TABLE_COLUMNS = (
        {"title": "ID du formulaire", "width": 20},
        {"title": "Nom", "width": 40},
        {"title": "Enregistrement(s)", "width": 20},
        {"title": "Type", "width": 20},
        {"title": "Date de création", "width": 20},
        {"title": "Date de modification", "width": 20},
    )
    EXPORT_FILE_NAME = "forms"
    EXPORT_ADDITIONAL_SERIALIZER_FIELDS = ("instance_updated_at", "instances_count")

    def get_queryset(self):
        form_objects = Form.objects
        if self.request.query_params.get("only_deleted", None):
            form_objects = Form.objects_only_deleted

        show_deleted = self.request.query_params.get("showDeleted", "false")
        if show_deleted == "true":
            form_objects = Form.objects_only_deleted

        queryset = form_objects.filter_for_user_and_app_id(self.request.user, self.request.query_params.get("app_id"))
        org_unit_id = self.request.query_params.get("orgUnitId", None)
        if org_unit_id:
            queryset = queryset.filter(instances__org_unit__id=org_unit_id)

        planning_ids = self.request.query_params.get("planning", None)
        if planning_ids:
            queryset = queryset.filter(plannings__id__in=planning_ids.split(","))

        org_unit_type_ids = self.request.query_params.get("orgUnitTypeIds")
        if org_unit_type_ids:
            queryset = queryset.filter(org_unit_types__id__in=org_unit_type_ids.split(","))

        projects_ids = self.request.query_params.get("projectsIds")
        if projects_ids:
            queryset = queryset.filter(projects__id__in=projects_ids.split(","))

        queryset = queryset.annotate(
            mapping_count=Count("mapping"),
            has_mappings=Case(
                When(mapping_count__gt=0, then=True),
                default=False,
                output_field=BooleanField(),
            ),
        )

        queryset = queryset.annotate(instance_updated_at=Max("instances__updated_at"))

        if not self.request.user.is_anonymous:
            profile = self.request.user.iaso_profile
        else:
            profile = False

        if profile and profile.org_units.exists():
            orgunits = OrgUnit.objects.hierarchy(profile.org_units.all())
            queryset = queryset.annotate(
                instances_count=Count(
                    "instances",
                    filter=(
                        ~Q(instances__file="")
                        & ~Q(instances__device__test_device=True)
                        & ~Q(instances__deleted=True)
                        & Q(instances__org_unit__in=orgunits)
                    ),
                    distinct=True,
                )
            )
        else:
            queryset = queryset.annotate(
                instances_count=Count(
                    "instances",
                    filter=(
                        ~Q(instances__file="") & ~Q(instances__device__test_device=True) & ~Q(instances__deleted=True)
                    ),
                    distinct=True,
                )
            )

        from_date = self.request.query_params.get("date_from", None)
        if from_date:
            queryset = queryset.filter(
                Q(instance_updated_at__gte=from_date) | Q(created_at__gte=from_date) | Q(updated_at__gte=from_date)
            )
        to_date = self.request.query_params.get("date_to", None)
        if to_date:
            parsed_to_date = parse_date(to_date) + timedelta(days=1)
            queryset = queryset.filter(
                Q(instance_updated_at__lt=parsed_to_date)
                | Q(created_at__lt=parsed_to_date)
                | Q(updated_at__lt=parsed_to_date)
            )

        org_unit_type_id = self.request.query_params.get("orgUnitTypeId", None)
        if org_unit_type_id:
            queryset = queryset.filter(org_unit_types__id=org_unit_type_id)

        search = self.request.query_params.get("search", None)
        if search:
            queryset = queryset.filter(name__icontains=search)

        # TODO: allow this only from a predefined list for security purposes
        order = self.request.query_params.get("order", "instance_updated_at").split(",")
        queryset = queryset.order_by(*order)

        return queryset

    def list(self, request: Request, *args, **kwargs):
        # TODO: use accept header to determine format - or at least the standard "format" parameter
        # DRF also provides a mechanic for custom renderer
        # see https://www.django-rest-framework.org/api-guide/renderers/
        csv_format = bool(request.query_params.get("csv"))
        xlsx_format = bool(request.query_params.get("xlsx"))

        if csv_format:
            return self.list_to_csv()
        elif xlsx_format:
            return self.list_to_xlsx()

        return super().list(request, *args, **kwargs)

    def list_to_csv(self):
        response = StreamingHttpResponse(
            streaming_content=(iter_items(self.get_queryset(), Echo(), self.EXPORT_TABLE_COLUMNS, self._get_table_row)),
            content_type=CONTENT_TYPE_CSV,
        )
        response["Content-Disposition"] = f"attachment; filename={self.EXPORT_FILE_NAME}.csv"

        return response

    def list_to_xlsx(self):
        response = HttpResponse(
            generate_xlsx("Forms", self.EXPORT_TABLE_COLUMNS, self.get_queryset(), self._get_table_row),
            content_type=CONTENT_TYPE_XLSX,
        )
        response["Content-Disposition"] = f"attachment; filename={self.EXPORT_FILE_NAME}.xlsx"

        return response

    def _get_table_row(self, form: typing.Mapping, **kwargs):  # TODO: use serializer
        form_data = self.get_serializer(form).data
        created_at = timestamp_to_datetime(form_data.get("created_at"))
        updated_at = (
            timestamp_to_datetime(form_data.get("instance_updated_at"))
            if form_data.get("instance_updated_at")
            else "2019-01-01 00:00:00"
        )
        org_unit_types = ", ".join([o["name"] for o in form_data.get("org_unit_types") if o is not None])
        return [
            form_data.get("form_id"),
            form_data.get("name"),
            form_data.get("instances_count"),
            org_unit_types,
            created_at,
            updated_at,
        ]

    def destroy(self, request, *args, **kwargs):
        original = get_object_or_404(Form, pk=self.kwargs["pk"])
        response = super(FormsViewSet, self).destroy(request, *args, **kwargs)
        destroyed_form = Form.objects_only_deleted.get(pk=original.id)
        log_modification(original, destroyed_form, FORM_API, user=request.user)
        return response

    FORM_PK = "form_pk"

    @action(detail=True, methods=["get"])
    def manifest(self, request, *args, **kwargs):
        """Returns a xml manifest file in the openrosa format for the Form

        This is used for the mobile app and Enketo to fetch the list of file attached to the Form
        see https://docs.getodk.org/openrosa-form-list/#the-manifest-document
        """
        form = self.get_object()
        attachments = form.attachments.all()
        media_files = []
        for attachment in attachments:
            attachment_file_url: str = attachment.file.url
            if not attachment_file_url.startswith("http"):
                # Needed for local dev
                attachment_file_url = public_url_for_enketo(request, attachment_file_url)

            media_files.append(
                f"""<mediaFile>
    <filename>{escape(attachment.name)}</filename>
    <hash>md5:{attachment.md5}</hash>
    <downloadUrl>{escape(attachment_file_url)}</downloadUrl>
</mediaFile>"""
            )

        nl = "\n"  # Backslashes are not allowed in f-string ¯\_(ツ)_/¯
        return HttpResponse(
            status=status.HTTP_200_OK,
            content_type="text/xml",
            headers={
                "X-OpenRosa-Version": "1.0",
            },
            content=f"""<?xml version="1.0" encoding="UTF-8"?>
<manifest xmlns="http://openrosa.org/xforms/xformsManifest">
{nl.join(media_files)}
</manifest>""",
        )


class MobileFormViewSet(FormsViewSet):
    # Filtering out forms without form versions to prevent mobile app from crashing
    def get_queryset(self):
        return super().get_queryset().exclude(form_versions=None)
