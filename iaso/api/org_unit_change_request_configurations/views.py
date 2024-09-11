import django_filters
from django.db.models import Q
from rest_framework import viewsets, filters, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response

from hat.audit.audit_mixin import AuditMixin
from iaso.api.org_unit_change_request_configurations.pagination import OrgUnitChangeRequestConfigurationPagination
from iaso.api.org_unit_change_request_configurations.serializers import (
    OrgUnitChangeRequestConfigurationListSerializer,
    OrgUnitChangeRequestConfigurationRetrieveSerializer,
    OrgUnitChangeRequestConfigurationWriteSerializer,
    OrgUnitChangeRequestConfigurationUpdateSerializer,
    OrgUnitTypeNestedSerializer,
)
from iaso.models import OrgUnitChangeRequestConfiguration, OrgUnitType, Project


class OrgUnitChangeRequestConfigurationViewSet(viewsets.ModelViewSet, AuditMixin):
    filter_backends = [filters.OrderingFilter, django_filters.rest_framework.DjangoFilterBackend]
    ordering_fields = [
        "id",
        "uuid",
        "project__name",
        "org_unit_type__name",
        "org_units_editable",
        "created_at",
        "updated_at",
        "created_by__username",
        "updated_by__username",
    ]
    http_method_names = ["get", "post", "patch", "delete"]
    pagination_class = OrgUnitChangeRequestConfigurationPagination

    def get_queryset(self):
        return (
            OrgUnitChangeRequestConfiguration.objects.order_by("id")
            .select_related("project", "org_unit_type", "created_by", "updated_by")
            .prefetch_related(
                "possible_types",
                "possible_parent_types",
                "group_sets",
                "editable_reference_forms",
                "other_groups",
            )
        )

    def get_serializer_class(self):
        if self.action == "create":
            return OrgUnitChangeRequestConfigurationWriteSerializer
        if self.action in ["list", "metadata"]:
            return OrgUnitChangeRequestConfigurationListSerializer
        if self.action == "retrieve":
            return OrgUnitChangeRequestConfigurationRetrieveSerializer
        if self.action == "partial_update":
            return OrgUnitChangeRequestConfigurationUpdateSerializer

    @action(detail=False)
    def check_availability(self, request, *args, **kwargs):
        user = request.user
        if user and user.is_anonymous:
            raise serializers.ValidationError("You must be logged in")

        # Not checking if this is indeed a number -> with django filters?
        project_id = self.request.query_params.get("project_id")
        if not project_id:
            raise serializers.ValidationError("Parameter project_id is missing")

        if not Project.objects.filter(id=project_id).exists():
            raise serializers.ValidationError("This project does not exist")

        # It seems there is currently no constraints on projects, but it will happen in the near future
        # user_projects = user.iaso_profile.projects.all()
        # if user_projects and project_id not in user_projects:
        #     raise serializers.ValidationError("You don't have access to this project")

        org_unit_types_in_configs = OrgUnitChangeRequestConfiguration.objects.filter(project_id=project_id).values_list(
            "org_unit_type_id", flat=True
        )
        available_org_unit_types = OrgUnitType.objects.filter(
            Q(projects__id=project_id) & ~Q(id__in=org_unit_types_in_configs)
        ).order_by("id")

        serializer = OrgUnitTypeNestedSerializer(available_org_unit_types, many=True)
        return Response(serializer.data)
