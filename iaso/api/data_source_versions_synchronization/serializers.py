from django.contrib.auth.models import User

from rest_framework import serializers

from iaso.api.common import DynamicFieldsModelSerializer
from iaso.models import (
    DataSourceVersionsSynchronization,
    SourceVersion,
    Account,
    OrgUnit,
    OrgUnitType,
)


class AccountNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ["id", "name", "default_version"]


class UserNestedSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="get_full_name", read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "full_name"]


class DataSourceVersionNestedSerializer(serializers.ModelSerializer):
    data_source_name = serializers.CharField(source="data_source.name", read_only=True)

    class Meta:
        model = SourceVersion
        fields = ["id", "number", "description", "data_source", "data_source_name"]


class DataSourceVersionsSynchronizationSerializer(DynamicFieldsModelSerializer):
    """
    Inheriting from DynamicFieldsModelSerializer allows to fetch the data with only a specific subset of fields.
    This is useful e.g. to build a dropdown in the UI with only the name and ID of objects.
    """

    class Meta:
        model = DataSourceVersionsSynchronization
        fields = [
            "id",
            "name",
            "source_version_to_update",
            "source_version_to_compare_with",
            "count_create",
            "count_update",
            "account",
            "created_by",
            "created_at",
            "updated_at",
        ]
        default_fields = [
            "id",
            "name",
            "source_version_to_update",
            "source_version_to_compare_with",
            "count_create",
            "count_update",
            "account",
            "created_by",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            "id": {"read_only": True},
            "count_create": {"read_only": True},
            "count_update": {"read_only": True},
            "account": {"read_only": True},
            "created_by": {"read_only": True},
            "created_at": {"read_only": True},
            "updated_at": {"read_only": True},
        }

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if "source_version_to_update" in self.fields:
            representation["source_version_to_update"] = DataSourceVersionNestedSerializer(
                instance.source_version_to_update, read_only=True
            ).data
        if "source_version_to_compare_with" in self.fields:
            representation["source_version_to_compare_with"] = DataSourceVersionNestedSerializer(
                instance.source_version_to_compare_with, read_only=True
            ).data
        if "account" in self.fields:
            representation["account"] = AccountNestedSerializer(instance.account, read_only=True).data
        if "created_by" in self.fields:
            representation["created_by"] = UserNestedSerializer(instance.created_by, read_only=True).data
        return representation

    def validate(self, validated_data):
        source_version_to_update = validated_data["source_version_to_update"]
        source_version_to_compare_with = validated_data["source_version_to_compare_with"]

        if source_version_to_update.data_source_id != source_version_to_compare_with.data_source_id:
            raise serializers.ValidationError("The two versions to compare must be linked to the same data source.")
        if source_version_to_update.pk == source_version_to_compare_with.pk:
            raise serializers.ValidationError("The two versions to compare must be different.")

        return validated_data


class CreateJsonDiffParametersSerializer(serializers.Serializer):
    """
    Validate the parameters of DataSourceVersionsSynchronization.create_json_diff().
    """

    # Version to update.
    source_version_to_update_validation_status = serializers.ChoiceField(
        choices=OrgUnit.VALIDATION_STATUS_CHOICES, required=False, default=None
    )
    source_version_to_update_top_org_unit = serializers.PrimaryKeyRelatedField(
        queryset=OrgUnit.objects.all(), required=False, default=None
    )
    source_version_to_update_org_unit_types = serializers.PrimaryKeyRelatedField(
        queryset=OrgUnitType.objects.all(), many=True, required=False, default=None
    )
    # Version to compare with.
    source_version_to_compare_with_validation_status = serializers.ChoiceField(
        choices=OrgUnit.VALIDATION_STATUS_CHOICES, required=False, default=None
    )
    source_version_to_compare_with_top_org_unit = serializers.PrimaryKeyRelatedField(
        queryset=OrgUnit.objects.all(), required=False, default=None
    )
    source_version_to_compare_with_org_unit_types = serializers.PrimaryKeyRelatedField(
        queryset=OrgUnitType.objects.all(), many=True, required=False, default=None
    )
    # Options.
    ignore_groups = serializers.BooleanField(required=False, default=False)
    show_deleted_org_units = serializers.BooleanField(required=False, default=False)
    field_names = serializers.MultipleChoiceField(
        choices=DataSourceVersionsSynchronization.SYNCHRONIZABLE_FIELDS, required=False, default=None
    )

    def validate_source_version_to_update_top_org_unit(self, top_org_unit: OrgUnit) -> OrgUnit:
        if top_org_unit:
            source_version = self.context["data_source_versions_synchronization"].source_version_to_update
            if top_org_unit.version != source_version:
                raise serializers.ValidationError(
                    f"The version of this org unit is different from the version to update."
                )
        return top_org_unit

    def validate_source_version_to_compare_with_top_org_unit(self, top_org_unit: OrgUnit) -> OrgUnit:
        if top_org_unit:
            source_version = self.context["data_source_versions_synchronization"].source_version_to_compare_with
            if top_org_unit.version != source_version:
                raise serializers.ValidationError(
                    f"The version of this org unit is different from the version to update."
                )
        return top_org_unit
