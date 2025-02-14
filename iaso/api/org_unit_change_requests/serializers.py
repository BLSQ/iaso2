import uuid

from rest_framework import serializers
from django.contrib.auth.models import User
from django.utils.translation import gettext as _
from hat.audit.audit_logger import AuditLogger
from hat.audit.models import ORG_UNIT_CHANGE_REQUEST_API, Modification
from iaso.api.mobile.org_units import ReferenceInstancesSerializer
from iaso.models import Instance, OrgUnit, OrgUnitChangeRequest, OrgUnitType
from iaso.models.payments import PaymentStatuses
from iaso.utils.serializer.id_or_uuid_field import IdOrUuidRelatedField
from iaso.utils.serializer.three_dim_point_field import ThreeDimPointField
from iaso.api.common import TimestampField
from iaso.utils import geojson_queryset


class UserNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name"]
        ref_name = "UserNestedSerializerForChangeRequest"


class OrgUnitNestedSerializer(serializers.ModelSerializer):
    geo_json = serializers.SerializerMethodField()

    class Meta:
        model = OrgUnit
        fields = ["id", "name", "geo_json"]
        ref_name = "OrgUnitNestedSerializerForChangeRequest"

    def get_geo_json(self, obj):
        if obj.simplified_geom:
            shape_queryset = OrgUnit.objects.filter(id=obj.id)
            return geojson_queryset(shape_queryset, geometry_field="simplified_geom")
        return None


class OrgUnitTypeNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrgUnitType
        fields = ["id", "name", "short_name"]
        ref_name = "OrgUnitTypeNestedSerializerForChangeRequest"


class InstanceForChangeRequestSerializer(serializers.ModelSerializer):
    """
    Used for nesting `Instance` instances.
    """

    form_name = serializers.CharField(source="form.name")
    values = serializers.JSONField(source="json")

    class Meta:
        model = Instance
        fields = [
            "id",
            "form_id",
            "form_name",
            "values",
        ]


class OrgUnitForChangeRequestSerializer(serializers.ModelSerializer):
    """
    Used for nesting `OrgUnit` instances.
    """

    parent = OrgUnitNestedSerializer()
    org_unit_type = OrgUnitTypeNestedSerializer()
    groups = serializers.SerializerMethodField(method_name="get_groups")
    location = ThreeDimPointField()
    reference_instances = InstanceForChangeRequestSerializer(many=True)

    class Meta:
        model = OrgUnit
        fields = [
            "id",
            "parent",
            "name",
            "org_unit_type",
            "groups",
            "location",
            "opening_date",
            "closed_date",
            "reference_instances",
            "validation_status",
        ]

    def get_groups(self, obj: OrgUnitChangeRequest):
        return [{"id": group.id, "name": group.name} for group in obj.groups.all()]


class MobileOrgUnitChangeRequestListSerializer(serializers.ModelSerializer):
    """
    Used to list many `OrgUnitChangeRequest` instances for mobile.
    """

    org_unit_id = serializers.IntegerField(source="org_unit.id")
    org_unit_uuid = serializers.UUIDField(source="org_unit.uuid")
    new_location = ThreeDimPointField()
    created_at = TimestampField()
    updated_at = TimestampField()
    new_reference_instances = ReferenceInstancesSerializer(many=True)

    class Meta:
        model = OrgUnitChangeRequest
        fields = [
            "id",
            "uuid",
            "org_unit_id",
            "org_unit_uuid",
            "status",
            "approved_fields",
            "rejection_comment",
            "created_at",
            "updated_at",
            "new_parent_id",
            "new_name",
            "new_org_unit_type_id",
            "new_groups",
            "new_location",
            "new_location_accuracy",
            "new_opening_date",
            "new_closed_date",
            "new_reference_instances",
        ]


class OrgUnitChangeRequestListSerializer(serializers.ModelSerializer):
    """
    Used to list many `OrgUnitChangeRequest` instances.
    """

    org_unit_id = serializers.IntegerField(source="org_unit.id")
    org_unit_uuid = serializers.UUIDField(source="org_unit.uuid")
    org_unit_name = serializers.CharField(source="org_unit.name")
    org_unit_parent_id = serializers.IntegerField(source="org_unit.parent.id", allow_null=True)
    org_unit_parent_name = serializers.CharField(source="org_unit.parent.name", allow_null=True)
    org_unit_validation_status = serializers.CharField(source="org_unit.validation_status")
    org_unit_type_id = serializers.IntegerField(source="org_unit.org_unit_type.id", allow_null=True)
    org_unit_type_name = serializers.CharField(source="org_unit.org_unit_type.name", allow_null=True)
    groups = serializers.SerializerMethodField(method_name="get_current_org_unit_groups")
    projects = serializers.SerializerMethodField(method_name="get_current_org_unit_type_projects")
    created_by = UserNestedSerializer()
    updated_by = UserNestedSerializer()
    created_at = TimestampField()
    updated_at = TimestampField()
    payment_status = serializers.SerializerMethodField(
        method_name="get_payment_status", allow_null=True, read_only=True
    )

    class Meta:
        model = OrgUnitChangeRequest
        fields = [
            "id",
            "uuid",
            "org_unit_id",
            "org_unit_uuid",
            "org_unit_name",
            "org_unit_parent_id",
            "org_unit_parent_name",
            "org_unit_validation_status",
            "org_unit_type_id",
            "org_unit_type_name",
            "status",
            "groups",
            "projects",
            "requested_fields",
            "approved_fields",
            "rejection_comment",
            "created_by",
            "created_at",
            "updated_by",
            "updated_at",
            "payment_status",
        ]

    def get_current_org_unit_groups(self, obj: OrgUnitChangeRequest):
        return [{"id": group.id, "name": group.name} for group in obj.org_unit.groups.all()]

    def get_current_org_unit_type_projects(self, obj: OrgUnitChangeRequest):
        return [{"id": project.id, "name": project.name} for project in obj.org_unit.org_unit_type.projects.all()]

    def get_payment_status(self, obj: OrgUnitChangeRequest):
        payment = obj.payment
        if payment is not None:
            return payment.get_status_display()
        potential_payment = obj.potential_payment
        if potential_payment is not None:
            return str(_(PaymentStatuses.PENDING.label))
        status = obj.status
        if status == OrgUnitChangeRequest.Statuses.APPROVED.value:
            return str(_(PaymentStatuses.PENDING.label))
        return None


class OrgUnitChangeRequestRetrieveSerializer(serializers.ModelSerializer):
    """
    Used to show one `OrgUnitChangeRequest` instance.
    """

    org_unit = OrgUnitForChangeRequestSerializer()
    created_by = UserNestedSerializer()
    updated_by = UserNestedSerializer()
    new_parent = OrgUnitNestedSerializer()
    new_org_unit_type = OrgUnitTypeNestedSerializer()
    new_groups = serializers.SerializerMethodField(method_name="get_new_groups")
    new_location = ThreeDimPointField()
    new_reference_instances = InstanceForChangeRequestSerializer(many=True)
    created_at = TimestampField()
    updated_at = TimestampField()
    old_parent = OrgUnitNestedSerializer()
    old_org_unit_type = OrgUnitTypeNestedSerializer()
    old_groups = serializers.SerializerMethodField(method_name="get_old_groups")
    old_location = ThreeDimPointField()
    old_reference_instances = InstanceForChangeRequestSerializer(many=True)

    class Meta:
        model = OrgUnitChangeRequest
        fields = [
            "id",
            "uuid",
            "status",
            "created_by",
            "created_at",
            "updated_by",
            "updated_at",
            "requested_fields",
            "approved_fields",
            "rejection_comment",
            "org_unit",
            "new_parent",
            "new_name",
            "new_org_unit_type",
            "new_groups",
            "new_location",
            "new_location_accuracy",
            "new_opening_date",
            "new_closed_date",
            "new_reference_instances",
            "old_parent",
            "old_name",
            "old_org_unit_type",
            "old_groups",
            "old_location",
            "old_opening_date",
            "old_closed_date",
            "old_reference_instances",
        ]

    def get_new_groups(self, obj: OrgUnitChangeRequest) -> list[dict]:
        return [{"id": group.id, "name": group.name} for group in obj.new_groups.all()]

    def get_old_groups(self, obj: OrgUnitChangeRequest) -> list[dict]:
        return [{"id": group.id, "name": group.name} for group in obj.old_groups.all()]


class OrgUnitChangeRequestWriteSerializer(serializers.ModelSerializer):
    """
    Used to create one `OrgUnitChangeRequest` instance.
    """

    id = serializers.IntegerField(read_only=True)
    uuid = serializers.UUIDField(required=False, default=uuid.uuid4)
    org_unit_id = IdOrUuidRelatedField(
        source="org_unit",
        queryset=OrgUnit.objects.all(),
        required=False,
    )
    new_parent_id = IdOrUuidRelatedField(
        source="new_parent",
        queryset=OrgUnit.objects.all(),
        required=False,
        allow_null=True,
    )
    new_org_unit_type_id = serializers.PrimaryKeyRelatedField(
        source="new_org_unit_type",
        queryset=OrgUnitType.objects.all(),
        required=False,
        allow_null=True,
    )
    new_location = ThreeDimPointField(
        required=False,
        allow_null=True,
    )
    new_reference_instances = IdOrUuidRelatedField(
        many=True,
        queryset=Instance.objects.all(),
        required=False,
    )

    class Meta:
        model = OrgUnitChangeRequest
        fields = [
            "id",
            "uuid",
            "org_unit_id",
            "new_parent_id",
            "new_name",
            "new_org_unit_type_id",
            "new_groups",
            "new_location",
            "new_location_accuracy",
            "new_opening_date",
            "new_closed_date",
            "new_reference_instances",
        ]
        extra_kwargs = {
            "new_groups": {"write_only": True},
            "new_reference_instances": {"write_only": True},
        }

    def validate_new_reference_instances(self, new_reference_instances):
        seen = []
        for instance in new_reference_instances:
            unique_org_unit_form = f"{instance.form_id}-{instance.org_unit_id}"
            if unique_org_unit_form in seen:
                raise serializers.ValidationError("Only one reference instance can exist by org_unit/form pair.")
            seen.append(unique_org_unit_form)
        return new_reference_instances

    def validate_new_org_unit_type_id(self, new_org_unit_type):
        request = self.context.get("request")
        if (
            request
            and new_org_unit_type
            and not new_org_unit_type.projects.filter(account=request.user.iaso_profile.account).exists()
        ):
            raise serializers.ValidationError("`new_org_unit_type_id` is not part of the user account.")
        return new_org_unit_type

    def validate(self, validated_data):
        # Fields names are different between API and model, e.g. `new_parent_id` VS `new_parent`.
        new_fields_api = [name for name in self.Meta.fields if name.startswith("new_")]

        new_closed_date = validated_data.get("new_closed_date")
        new_opening_date = validated_data.get("new_opening_date")
        new_parent = validated_data.get("new_parent")
        org_unit = validated_data.get("org_unit")

        if (new_opening_date and new_closed_date) and (new_closed_date <= new_opening_date):
            raise serializers.ValidationError("`new_closed_date` must be later than `new_opening_date`.")
        elif (org_unit.closed_date and new_opening_date) and (new_opening_date >= org_unit.closed_date):
            raise serializers.ValidationError("`new_opening_date` must be before the current org_unit closed date.")

        if org_unit and new_parent:
            if new_parent.version_id != org_unit.version_id:
                raise serializers.ValidationError("`new_parent_id` and `org_unit_id` must have the same version.")

            if OrgUnit.objects.hierarchy(org_unit).filter(pk=new_parent.pk).exists():
                raise serializers.ValidationError("`new_parent_id` is already a child of `org_unit_id`.")

        # All `new_*` fields passed in the payload are those for which the user requests a change.
        # If a value is None or "" (depending on what the field refers to in the model), it means
        # the user is asking to erase the value of this field (e.g. reset a `closed_date`).
        validated_data["requested_fields"] = [
            field for field in validated_data if field in OrgUnitChangeRequest.get_new_fields()
        ]

        if not validated_data["requested_fields"]:
            raise serializers.ValidationError(
                f"You must provide at least one of the following fields: {', '.join(new_fields_api)}."
            )

        return validated_data


class OrgUnitChangeRequestReviewSerializer(serializers.ModelSerializer):
    """
    Used to approve or reject one `OrgUnitChangeRequest`.
    """

    class Meta:
        model = OrgUnitChangeRequest
        fields = [
            "status",
            "approved_fields",
            "rejection_comment",
        ]

    def validate_status(self, value):
        approved = OrgUnitChangeRequest.Statuses.APPROVED
        rejected = OrgUnitChangeRequest.Statuses.REJECTED
        if value not in [approved, rejected]:
            raise serializers.ValidationError(f"Must be `{approved}` or `{rejected}`.")
        return value

    def validate(self, validated_data):
        instance = OrgUnitChangeRequest(**validated_data)
        instance.clean()

        status = validated_data.get("status")
        approved_fields = validated_data.get("approved_fields")
        rejection_comment = validated_data.get("rejection_comment")

        if status == OrgUnitChangeRequest.Statuses.REJECTED and not rejection_comment:
            raise serializers.ValidationError("A `rejection_comment` must be provided.")

        if status == OrgUnitChangeRequest.Statuses.APPROVED and not approved_fields:
            raise serializers.ValidationError("At least one `approved_fields` must be provided.")

        return validated_data


class OrgUnitChangeRequestBulkReviewSerializer(serializers.Serializer):
    """
    Bulk-approve or bulk-reject `OrgUnitChangeRequest`s.
    """

    # Selection.
    select_all = serializers.BooleanField(default=False)
    selected_ids = serializers.ListField(child=serializers.IntegerField(min_value=1))
    unselected_ids = serializers.ListField(child=serializers.IntegerField(min_value=1))
    # Review data.
    status = serializers.ChoiceField(choices=OrgUnitChangeRequest.Statuses, default=None)
    approved_fields = serializers.MultipleChoiceField(choices=OrgUnitChangeRequest.get_new_fields(), default=None)
    rejection_comment = serializers.CharField(required=False, default="")

    def validate_status(self, value):
        approved = OrgUnitChangeRequest.Statuses.APPROVED
        rejected = OrgUnitChangeRequest.Statuses.REJECTED
        if value not in [approved, rejected]:
            raise serializers.ValidationError(f"Must be `{approved}` or `{rejected}`.")
        return value

    def validate(self, validated_data):
        status = validated_data["status"]
        rejection_comment = validated_data["rejection_comment"]
        approved_fields = validated_data["approved_fields"]

        if status == OrgUnitChangeRequest.Statuses.REJECTED and not rejection_comment:
            raise serializers.ValidationError("A `rejection_comment` must be provided.")

        if status == OrgUnitChangeRequest.Statuses.APPROVED and not approved_fields:
            raise serializers.ValidationError("At least one `approved_fields` must be provided.")

        return validated_data


class AuditOrgUnitChangeRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrgUnitChangeRequest
        fields = "__all__"


class OrgUnitChangeRequestAuditLogger(AuditLogger):
    serializer = AuditOrgUnitChangeRequestSerializer
    default_source = ORG_UNIT_CHANGE_REQUEST_API
