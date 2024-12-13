from django.contrib.auth.models import User
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend  # type: ignore
from rest_framework import serializers, filters
from rest_framework.decorators import action
from rest_framework.fields import Field
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from hat.audit.audit_mixin import AuditMixin
from iaso.permissions import ReadOnly

from hat.audit.models import Modification
from iaso.api.common import (
    ModelViewSet,
    DeletionFilterBackend,
    ReadOnlyOrHasPermission,
    TimestampField,
    DateTimestampField,
)
from iaso.models import Project, OrgUnit, Form, OrgUnitType
from iaso.models.microplanning import Team, TeamType, Planning, Assignment
from iaso.models.org_unit import OrgUnitQuerySet
from hat.menupermissions import models as permission


class NestedProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ["id", "name"]


class NestedTeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ["id", "name", "deleted_at"]


class NestedUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username"]


class AuditTeamSerializer(serializers.ModelSerializer):
    sub_teams: Field = serializers.PrimaryKeyRelatedField(read_only=True, many=True)

    class Meta:
        model = Team
        fields = "__all__"


class NestedOrgUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrgUnit
        fields = ["id", "name", "org_unit_type"]


class TeamSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.context["request"].user
        account = user.iaso_profile.account
        users_in_account = User.objects.filter(iaso_profile__account=account)
        self.fields["project"].queryset = account.project_set.all()
        self.fields["manager"].queryset = users_in_account
        self.fields["users"].child_relation.queryset = users_in_account
        self.fields["sub_teams"].child_relation.queryset = Team.objects.filter_for_user(user)
        self.fields["parent"].queryset = Team.objects.filter_for_user(user)

    class Meta:
        model = Team
        fields = [
            "id",
            "project",
            "project_details",
            "name",
            "description",
            "created_at",
            "deleted_at",
            "type",
            "users",
            "users_details",
            "manager",
            "parent",
            "sub_teams",
            "sub_teams_details",
        ]
        read_only_fields = ["created_at"]

    users_details = NestedUserSerializer(many=True, read_only=True, source="users")
    sub_teams_details = NestedTeamSerializer(many=True, read_only=True, source="sub_teams")
    project_details = NestedProjectSerializer(many=False, read_only=True, source="project")

    def validate_parent(self, value: Team):
        if value is not None and value.type not in (None, TeamType.TEAM_OF_TEAMS):
            raise serializers.ValidationError("parentIsNotTeamOfTeam")
        if self.instance:
            p = value
            while p:
                if p == self.instance:
                    raise serializers.ValidationError("noLoopInSubTree")
                # TODO: investigate type error on next line
                p = p.parent  # type: ignore
        return value

    def validate_sub_teams(self, values):
        def recursive_check(instance, children):
            for child in children:
                if instance == child:
                    raise serializers.ValidationError("noLoopInSubTree")
                recursive_check(instance, child.sub_teams.all())

        if self.instance:
            recursive_check(self.instance, values)
        return values

    def save(self, **kwargs):
        old_sub_teams_ids = []
        if self.instance:
            old_sub_teams_ids = list(self.instance.sub_teams.all().values_list("id", flat=True))
        r = super().save(**kwargs)
        new_sub_teams_ids = list(self.instance.sub_teams.all().values_list("id", flat=True))
        team_changed_qs = Team.objects.filter(id__in=new_sub_teams_ids + old_sub_teams_ids)
        teams_to_update = []
        for team in team_changed_qs:
            teams_to_update += team.calculate_paths(force_recalculate=True)
        Team.objects.bulk_update(teams_to_update, ["path"])
        return r

    def validate(self, attrs):
        validated_data = super().validate(attrs)

        user = self.context["request"].user
        validated_data["created_by"] = user

        project = validated_data.get("project", self.instance.project if self.instance else None)
        sub_teams = validated_data.get("sub_teams", self.instance.sub_teams.all() if self.instance else [])
        for sub_team in sub_teams:
            if sub_team.project != project:
                raise serializers.ValidationError("Sub teams must be in the same project")

        # Check that we don't have both user and teams
        # this is written in this way to support partial update
        users = None
        teams = None
        if self.instance:
            teams = self.instance.sub_teams.all()
            users = self.instance.users.all()
        if "sub_teams" in validated_data:
            teams = validated_data["sub_teams"]
        if "users" in validated_data:
            users = validated_data["users"]
        if teams and users:
            raise serializers.ValidationError("Teams cannot have both users and sub teams")
        if users:
            expected_type = TeamType.TEAM_OF_USERS
        elif teams:
            expected_type = TeamType.TEAM_OF_TEAMS
        else:
            expected_type = None
        if validated_data.get("type") and expected_type and expected_type != validated_data.get("type"):
            raise serializers.ValidationError("Incorrect type")
        if validated_data.get("type") is None:
            validated_data["type"] = expected_type

        return validated_data


class TeamManagersFilterBackend(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        managers = request.GET.get("managers", None)
        if managers:
            manager_ids = [int(val) for val in managers.split(",") if val.isnumeric()]
            return queryset.filter(manager_id__in=manager_ids)
        return queryset


class TeamProjectsFilterBackend(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        projects = request.GET.get("projects", None)
        if projects:
            project_ids = [int(val) for val in projects.split(",") if val.isnumeric()]
            return queryset.filter(project_id__in=project_ids)
        return queryset


class TeamTypesFilterBackend(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        types = request.GET.get("types", None)
        if types:
            team_types = [val for val in types.split(",") if TeamType.is_valid_team_type(val)]
            return queryset.filter(type__in=team_types)
        return queryset


class TeamSearchFilterBackend(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        search = request.query_params.get("search")

        if search:
            queryset = queryset.filter(Q(name__icontains=search)).distinct()

        return queryset


class TeamAncestorFilterBackend(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        ancestor_id = request.query_params.get("ancestor")

        if ancestor_id:
            try:
                ancestor = Team.objects.get(pk=ancestor_id)
            except Team.DoesNotExist:
                raise serializers.ValidationError(
                    {"ancestor": "Select a valid choice. That choice is not one of the available choices."}
                )
            queryset = queryset.filter(path__descendants=ancestor.path)

        return queryset


class TeamViewSet(AuditMixin, ModelViewSet):
    """Api for teams

    Read access for all auth users.
    Write access necessitate iaso_teams permissions.
    The tree assignation are handled by settings the child subteams (parent is readonly)
    """

    remove_results_key_if_paginated = True
    filter_backends = [
        TeamAncestorFilterBackend,
        filters.OrderingFilter,
        DjangoFilterBackend,
        TeamSearchFilterBackend,
        DeletionFilterBackend,
        TeamManagersFilterBackend,
        TeamTypesFilterBackend,
        TeamProjectsFilterBackend,
    ]
    permission_classes = [ReadOnlyOrHasPermission(permission.TEAMS)]  # type: ignore
    serializer_class = TeamSerializer
    queryset = Team.objects.all()
    ordering_fields = ["id", "project__name", "name", "created_at", "updated_at", "type"]
    filterset_fields = {
        "id": ["in"],
        "name": ["icontains"],
        "project": ["exact"],
    }

    audit_serializer = AuditTeamSerializer  # type: ignore

    def get_queryset(self):
        user = self.request.user
        return self.queryset.filter_for_user(user)


class PlanningSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.context["request"].user
        account = user.iaso_profile.account
        self.fields["project"].queryset = account.project_set.all()
        self.fields["team"].queryset = Team.objects.filter_for_user(user)
        self.fields["org_unit"].queryset = OrgUnit.objects.filter_for_user_and_app_id(user, None)
        self.fields["forms"].child_relation.queryset = Form.objects.filter_for_user_and_app_id(user).distinct()

    class Meta:
        model = Planning
        fields = [
            "id",
            "name",
            "team_details",
            "team",
            "org_unit",
            "org_unit_details",
            "forms",
            "project",
            "project_details",
            "description",
            "published_at",
            "started_at",
            "ended_at",
        ]
        read_only_fields = ["created_at", "parent"]

    team_details = NestedTeamSerializer(source="team", read_only=True)
    org_unit_details = NestedOrgUnitSerializer(source="org_unit", read_only=True)
    project_details = NestedProjectSerializer(source="project", read_only=True)

    def validate(self, attrs):
        validated_data = super().validate(attrs)

        user = self.context["request"].user
        validated_data["created_by"] = user
        validation_errors = {}
        if (
            validated_data.get("started_at")
            and validated_data.get("ended_at")
            and validated_data["started_at"] > validated_data["ended_at"]
        ):
            validation_errors["started_at"] = "startDateAfterEndDate"
            validation_errors["ended_at"] = "EndDateBeforeStartDate"
        project = validated_data.get("project", self.instance.project if self.instance else None)

        team = validated_data.get("team", self.instance.team if self.instance else None)
        if team.project != project:
            validation_errors["team"] = "planningAndTeams"

        forms = validated_data.get("forms", self.instance.forms if self.instance else None)
        for form in forms:
            if not form in project.forms.all():
                validation_errors["forms"] = "planningAndForms"

        org_unit = validated_data.get("org_unit", self.instance.org_unit if self.instance else None)
        if org_unit and org_unit.org_unit_type:
            org_unit_projects = org_unit.org_unit_type.projects.all()
            if not project in org_unit_projects:
                validation_errors["org_unit"] = "planningAndOrgUnit"
        if validation_errors:
            raise serializers.ValidationError(validation_errors)

        return validated_data


class AuditPlanningSerializer(serializers.ModelSerializer):
    class Meta:
        model = Planning
        fields = "__all__"


class PlanningSearchFilterBackend(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        search = request.query_params.get("search")

        if search:
            queryset = queryset.filter(Q(name__icontains=search)).distinct()
        return queryset


class PublishingStatusFilterBackend(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        status = request.query_params.get("publishing_status", "all")
        form_ids = request.query_params.get("form_ids", None)

        if status == "draft":
            queryset = queryset.filter(published_at__isnull=True)
        if status == "published":
            queryset = queryset.exclude(published_at__isnull=True)
        if form_ids:
            queryset = queryset.filter(forms__id__in=form_ids.split(","))
        return queryset


class PlanningViewSet(AuditMixin, ModelViewSet):
    remove_results_key_if_paginated = True
    permission_classes = [ReadOnlyOrHasPermission(permission.PLANNING_WRITE)]  # type: ignore
    serializer_class = PlanningSerializer
    queryset = Planning.objects.all()
    filter_backends = [
        filters.OrderingFilter,
        DjangoFilterBackend,
        PublishingStatusFilterBackend,
        PlanningSearchFilterBackend,
        DeletionFilterBackend,
    ]
    ordering_fields = ["id", "name", "started_at", "ended_at", "project__name", "org_unit__name"]
    filterset_fields = {
        "name": ["icontains"],
        "started_at": ["gte", "lte"],
        "ended_at": ["gte", "lte"],
    }
    audit_serializer = AuditPlanningSerializer  # type: ignore

    def get_queryset(self):
        user = self.request.user
        return self.queryset.filter_for_user(user)


class AssignmentSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.context["request"].user
        account = user.iaso_profile.account
        users_in_account = User.objects.filter(iaso_profile__account=account)

        self.fields["user"].queryset = users_in_account
        self.fields["planning"].queryset = Planning.objects.filter_for_user(user)
        self.fields["team"].queryset = Team.objects.filter_for_user(user)
        self.fields["org_unit"].queryset = OrgUnit.objects.filter_for_user_and_app_id(user, None)

    class Meta:
        model = Assignment
        fields = ["id", "planning", "user", "team", "org_unit", "org_unit_details"]
        read_only_fields = ["created_at"]

    org_unit_details = NestedOrgUnitSerializer(source="org_unit", read_only=True)

    def validate(self, attrs):
        validated_data = super().validate(attrs)

        user = self.context["request"].user
        validated_data["created_by"] = user

        assigned_user = validated_data.get("user", self.instance.user if self.instance else None)
        assigned_team = validated_data.get("team", self.instance.team if self.instance else None)
        if assigned_team and assigned_user:
            raise serializers.ValidationError("Cannot assign on both team and users")

        planning = validated_data.get("planning", self.instance.planning if self.instance else None)
        org_unit: OrgUnit = validated_data.get("org_unit", self.instance.org_unit if self.instance else None)

        org_units_available: OrgUnitQuerySet = self.fields["org_unit"].queryset
        org_units_available = org_units_available.descendants(planning.org_unit)
        if org_unit not in org_units_available:
            raise serializers.ValidationError({"org_unit": "OrgUnit is not in planning scope"})
        # TODO More complex check possible:
        # - Team or user should be under the root planning team
        # - check that the hierarchy of the planning assignement is respected
        # - one of the parent org unit should be assigned to a parent team of the assigned user or team
        # - type  of org unit is valid for this form
        return validated_data


class AuditAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment
        fields = "__all__"


class BulkAssignmentSerializer(serializers.Serializer):
    """Assign orgunit in bulk to as team or user.

    update assignment object if it exists otherwise create it
    Audit the modification"""

    planning = serializers.PrimaryKeyRelatedField(queryset=Planning.objects.none(), write_only=True)
    team = serializers.PrimaryKeyRelatedField(
        queryset=Team.objects.none(), write_only=True, required=False, allow_null=True
    )
    user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.none(), write_only=True, required=False, allow_null=True
    )
    org_units = serializers.PrimaryKeyRelatedField(queryset=OrgUnit.objects.none(), write_only=True, many=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.context["request"].user
        account = user.iaso_profile.account
        users_in_account = User.objects.filter(iaso_profile__account=account)

        self.fields["user"].queryset = users_in_account
        self.fields["planning"].queryset = Planning.objects.filter_for_user(user)
        self.fields["team"].queryset = Team.objects.filter_for_user(user)
        self.fields["org_units"].child_relation.queryset = OrgUnit.objects.filter_for_user_and_app_id(user, None)

    def validate(self, attrs):
        validated_data = super().validate(attrs)
        if validated_data.get("user") and validated_data.get("team"):
            raise serializers.ValidationError(
                {"team": "Cannot specify both user and teams", "user": "Cannot specify both user and teams"}
            )
        return validated_data

    def save(self, **kwargs):
        team = self.validated_data.get("team")
        user = self.validated_data.get("user")
        planning = self.validated_data["planning"]
        request = self.context["request"]
        requester = request.user
        assignments_list = []
        for org_unit in self.validated_data["org_units"]:
            assignment, created = Assignment.objects.get_or_create(
                planning=planning, org_unit=org_unit, defaults={"created_by": requester}
            )
            old_value = []
            if not created:
                old_value = [AuditAssignmentSerializer(instance=assignment).data]

            assignment.deleted_at = None
            assignment.team = team
            assignment.user = user
            assignments_list.append(assignment)
            assignment.save()

            new_value = [AuditAssignmentSerializer(instance=assignment).data]
            Modification.objects.create(
                user=requester,
                past_value=old_value,
                new_value=new_value,
                content_object=assignment,
                source="API " + request.method + request.path,
            )
        return assignments_list


class AssignmentViewSet(AuditMixin, ModelViewSet):
    """Use the same permission as planning. Multi tenancy is done via the planning. An assignment don't make much
    sense outside of it's planning."""

    remove_results_key_if_paginated = True
    permission_classes = [IsAuthenticated, ReadOnlyOrHasPermission(permission.PLANNING_WRITE)]  # type: ignore
    serializer_class = AssignmentSerializer
    queryset = Assignment.objects.all()
    filter_backends = [
        filters.OrderingFilter,
        DjangoFilterBackend,
        PublishingStatusFilterBackend,
        DeletionFilterBackend,
    ]
    ordering_fields = ["id", "team__name", "user__username"]
    filterset_fields = {
        "planning": ["exact"],
        "team": ["exact"],
    }
    audit_serializer = AuditAssignmentSerializer  # type: ignore

    def get_queryset(self):
        user = self.request.user
        return self.queryset.filter_for_user(user)

    @action(methods=["POST"], detail=False)
    def bulk_create_assignments(self, request):
        serializer = BulkAssignmentSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        assignments_list = serializer.save()
        return_serializer = AssignmentSerializer(assignments_list, many=True, context={"request": request})
        return Response(return_serializer.data)


# noinspection PyMethodMayBeStatic
class MobilePlanningSerializer(serializers.ModelSerializer):
    "Only used to serialize for mobile"

    def save(self):
        # ensure that we can't save from here
        raise NotImplemented

    class Meta:
        model = Planning
        fields = [
            "id",
            "name",
            "description",
            "created_at",
            "started_at",
            "ended_at",
            "assignments",
        ]

    created_at = TimestampField()
    started_at = DateTimestampField()
    ended_at = DateTimestampField()

    assignments = serializers.SerializerMethodField()

    def get_assignments(self, planning: Planning):
        user = self.context["request"].user
        r = []
        planning_form_set = set(planning.forms.values_list("id", flat=True))
        forms_per_ou_type = {}
        for out in OrgUnitType.objects.filter(projects__account=user.iaso_profile.account):
            out_set = set(out.form_set.values_list("id", flat=True))
            intersection = out_set.intersection(planning_form_set)
            forms_per_ou_type[out.id] = (
                intersection  # intersection of the two sets: the forms of the orgunit types and the forms of the planning
            )

        for a in planning.assignment_set.filter(deleted_at__isnull=True).filter(user=user).prefetch_related("org_unit"):
            # TODO: investigate type error on next line
            r.append({"org_unit_id": a.org_unit_id, "form_ids": forms_per_ou_type[a.org_unit.org_unit_type_id]})  # type: ignore
        return r


class MobilePlanningViewSet(ModelViewSet):
    """Planning for mobile, contrary to the more general API.
    it only returns the Planning where the user has assigned OrgUnit
    and his assignments
    """

    remove_results_key_if_paginated = False
    results_key = "plannings"
    permission_classes = [IsAuthenticated, ReadOnly]
    serializer_class = MobilePlanningSerializer

    def get_queryset(self):
        user = self.request.user
        # Only return  planning which 1. contain assignment for user 2. are published 3. undeleted
        # distinct is necessary otherwise if a planning contain multiple assignment for the same user it got duplicated

        return (
            Planning.objects.filter(assignment__user=user)
            .exclude(published_at__isnull=True)
            .filter(deleted_at__isnull=True)
            .distinct()
        )
