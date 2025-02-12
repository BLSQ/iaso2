from rest_framework import serializers
from iaso.models import MetricType, MetricValue


class MetricTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MetricType
        fields = [
            "id",
            "account",
            "name",
            "description",
            "source",
            "units",
            "comments",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class MetricValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = MetricValue
        fields = ["id", "metric_type", "org_unit", "year", "value"]
