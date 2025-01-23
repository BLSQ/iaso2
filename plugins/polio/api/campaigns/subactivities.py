from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend  # type: ignore
from rest_framework import permissions, serializers

from iaso.api.common import ModelViewSet
from iaso.models import Group
from plugins.polio.api.shared_serializers import GroupSerializer
from plugins.polio.models import Round, SubActivity, SubActivityScope


class SubActivityScopeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubActivityScope
        fields = ["group", "vaccine"]

    group = GroupSerializer(required=False)


class SubActivityCreateUpdateSerializer(serializers.ModelSerializer):
    round_number = serializers.IntegerField(write_only=True, required=False)
    campaign = serializers.CharField(write_only=True, required=False)
    scopes = SubActivityScopeSerializer(many=True, required=False)

    class Meta:
        model = SubActivity
        fields = [
            "id",
            "round_number",
            "campaign",
            "name",
            "start_date",
            "end_date",
            "scopes",
            "age_unit",
            "age_min",
            "age_max",
            "lqas_ended_at",
            "lqas_started_at",
            "im_ended_at",
            "im_started_at",
        ]

    def create(self, validated_data):
        round_number = validated_data.pop("round_number", None)
        campaign = validated_data.pop("campaign", None)
        scopes_data = validated_data.pop("scopes", [])

        if round_number is not None and campaign is not None:
            the_round = get_object_or_404(Round, campaign__obr_name=campaign, number=round_number)
            validated_data["round"] = the_round

            if self.context["request"].user.iaso_profile.account != the_round.campaign.account:
                raise serializers.ValidationError(
                    "You do not have permission to create a SubActivity for this Campaign."
                )

        else:
            raise serializers.ValidationError("Both round_number and campaign must be provided.")

        sub_activity = super().create(validated_data)

        for scope_data in scopes_data:
            group_data = scope_data.pop("group")
            group_data["source_version"] = self.context["request"].user.iaso_profile.account.default_version
            group_org_units = group_data.pop("org_units", [])
            group = Group.objects.create(**group_data)
            group.org_units.set(group_org_units)
            new_scope = SubActivityScope.objects.create(subactivity=sub_activity, group=group, **scope_data)
            group.name = f"scope {new_scope.id} for sub-activity {sub_activity.id} for round {round_number} of campaign {campaign}"
            group.save()

        return sub_activity

    def update(self, instance, validated_data):
        scopes_data = validated_data.pop("scopes", None)

        if scopes_data is not None:
            # Get the groups associated with the current scopes
            groups_to_check = [scope.group for scope in instance.scopes.all()]

            # Delete the scopes
            instance.scopes.all().delete()

            # Check if the groups are used by any other SubActivityScope
            for group in groups_to_check:
                if not SubActivityScope.objects.filter(group=group).exists():
                    group.delete()

            for scope_data in scopes_data:
                group_data = scope_data.pop("group")
                group_data["source_version"] = self.context["request"].user.iaso_profile.account.default_version
                group_org_units = group_data.pop("org_units", [])
                group = Group.objects.create(**group_data)
                group.org_units.set(group_org_units)
                SubActivityScope.objects.create(subactivity=instance, group=group, **scope_data)

        return super().update(instance, validated_data)


class SubActivityListDetailSerializer(serializers.ModelSerializer):
    round_id = serializers.IntegerField(source="round.id", read_only=True)
    scopes = SubActivityScopeSerializer(many=True)

    class Meta:
        model = SubActivity
        fields = [
            "id",
            "round_id",
            "name",
            "start_date",
            "end_date",
            "scopes",
            "age_unit",
            "age_min",
            "age_max",
            "lqas_ended_at",
            "lqas_started_at",
            "im_ended_at",
            "im_started_at",
        ]


class SubActivityViewSet(ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "head", "options", "post", "delete", "put"]
    model = SubActivity
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {"round__campaign__obr_name": ["exact"], "round__id": ["exact"]}

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return SubActivityCreateUpdateSerializer
        return SubActivityListDetailSerializer

    def get_queryset(self):
        return SubActivity.objects.filter(round__campaign__account=self.request.user.iaso_profile.account)

    def check_object_permissions(self, request, obj):
        super().check_object_permissions(request, obj)
        if request.user.iaso_profile.account != obj.round.campaign.account:
            self.permission_denied(request, message="Cannot access campaign")
