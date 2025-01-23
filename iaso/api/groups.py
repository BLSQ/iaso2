from django.db.models import Count
from iaso.api.group_sets.serializers import GroupSetSerializer
from rest_framework import permissions, serializers
from rest_framework.decorators import action
from rest_framework.response import Response

from hat.menupermissions import models as permission
from iaso.models import DataSource, Group, Project, SourceVersion

from .common import HasPermission, ModelViewSet, TimestampField


class HasGroupPermission(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if obj.source_version.data_source.read_only and request.method != "GET":
            return False

        user_account = request.user.iaso_profile.account
        projects = obj.source_version.data_source.projects.all()
        account_ids = [p.account_id for p in projects]

        return user_account.id in account_ids


class DataSourceSerializerForGroup(serializers.ModelSerializer):
    class Meta:
        model = DataSource
        fields = ["id", "name"]


class SourceVersionSerializerForGroup(serializers.ModelSerializer):
    class Meta:
        model = SourceVersion
        fields = ["id", "number", "data_source"]

    data_source = DataSourceSerializerForGroup()


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = [
            "id",
            "name",
            "source_ref",
            "source_version",
            "group_sets",
            "org_unit_count",
            "created_at",
            "updated_at",
            "block_of_countries",  # It's used to mark a group containing only countries
        ]
        read_only_fields = ["id", "source_version", "group_sets", "org_unit_count", "created_at", "updated_at"]
        ref_name = "iaso_group_serializer"

    source_version = SourceVersionSerializerForGroup(read_only=True)
    group_sets = GroupSetSerializer(many=True, read_only=True)
    org_unit_count = serializers.IntegerField(read_only=True)
    created_at = TimestampField(read_only=True)
    updated_at = TimestampField(read_only=True)

    def create(self, validated_data):
        profile = self.context["request"].user.iaso_profile
        version = profile.account.default_version

        if version is None:
            raise serializers.ValidationError("This account has no default version")

        validated_data["source_version"] = version

        return super().create(validated_data)


class GroupDropdownSerializer(serializers.ModelSerializer):
    label = serializers.SerializerMethodField()

    def get_label(self, obj):
        datasource = obj.source_version.data_source.name
        version_number = obj.source_version.number
        name = obj.name
        return f"{name} ({datasource} - {version_number})"

    class Meta:
        model = Group
        fields = ["id", "name", "label"]
        read_only_fields = ["id", "name", "label"]


class GroupsViewSet(ModelViewSet):
    f"""Groups API

    This API is restricted to users having the "{permission.ORG_UNITS}", "{permission.ORG_UNITS_READ}" and "{permission.COMPLETENESS_STATS}" permission

    GET /api/groups/
    GET /api/groups/<id>
    POST /api/groups/
    PATCH /api/groups/<id>
    DELETE /api/groups/<id>
    """

    permission_classes = [
        permissions.IsAuthenticated,
        HasPermission(permission.ORG_UNITS, permission.ORG_UNITS_READ, permission.COMPLETENESS_STATS),  # type: ignore
        HasGroupPermission,
    ]
    serializer_class = GroupSerializer
    results_key = "groups"
    http_method_names = ["get", "post", "patch", "delete", "head", "options", "trace"]

    def get_queryset(self):
        if self.request.user.is_anonymous:
            return Group.objects.none()

        profile = self.request.user.iaso_profile
        queryset = Group.objects.filter(
            source_version__data_source__projects__in=profile.account.project_set.all()
        ).prefetch_related("group_sets")
        return queryset

    def filter_queryset(self, queryset, allow_anon=False):
        light = self.request.GET.get("light", False)
        queryset = queryset.prefetch_related("source_version")
        queryset = queryset.prefetch_related("source_version__data_source")
        if not light:
            queryset = queryset.annotate(org_unit_count=Count("org_units"))

        version = self.request.query_params.get("version", None)
        data_source_id = self.request.GET.get("dataSource", None)
        if version:
            queryset = queryset.filter(source_version=version)
        elif data_source_id:
            queryset = queryset.filter(source_version__data_source__id=data_source_id)
        # if allow_anon is True, versions and projects are handled manually outside of this method
        elif not allow_anon:
            default_version = self.request.GET.get("defaultVersion", None)
            if default_version == "true":
                queryset = queryset.filter(source_version=self.request.user.iaso_profile.account.default_version)

            project_ids = self.request.GET.get("projectIds", None)
            if project_ids:
                versions = SourceVersion.objects.filter(data_source__projects__in=project_ids.split(","))
                queryset = queryset.filter(source_version__in=versions)

        block_of_countries = self.request.GET.get("blockOfCountries", None)
        if block_of_countries:  # Filter only org unit groups containing only countries as orgUnits
            queryset = queryset.filter(block_of_countries=block_of_countries)

        search = self.request.query_params.get("search", None)
        if search:
            queryset = queryset.filter(name__icontains=search)

        order = self.request.query_params.get("order", "name").split(",")

        return queryset.order_by(*order)

    @action(permission_classes=[], detail=False, methods=["GET"], serializer_class=GroupDropdownSerializer)
    def dropdown(self, request, *args):
        """To be used in dropdowns (filters)

        * Read only
        * Readable anonymously if feature flag on project allow them and an app_id parameter is passed
        * No permission needed
        """

        app_id = self.request.query_params.get("app_id")
        user = request.user
        if user and user.is_anonymous and app_id is None:
            raise serializers.ValidationError("Parameter app_id is missing")

        if user and user.is_authenticated:
            account = user.iaso_profile.account
            # Filter on version ids (linked to the account)""
            default_version_id = account.default_version.id
            versions = SourceVersion.objects.filter(data_source__projects__account=account)

        else:
            # this check if project need auth
            project = Project.objects.get_for_user_and_app_id(user, app_id)
            default_version_id = project.account.default_version.id
            versions = SourceVersion.objects.filter(data_source__projects=project)

        # Apply defaultVersion filter that we skip in filter_queryset when allowing anon users
        if self.request.GET.get("defaultVersion", None) == "true":
            versions = versions.filter(pk=default_version_id)

        groups = Group.objects.filter(source_version__in=versions).distinct()

        queryset = self.filter_queryset(groups, allow_anon=True)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
