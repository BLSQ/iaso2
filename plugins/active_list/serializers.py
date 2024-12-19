from rest_framework import serializers
from .models import Validation


class ValidationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Validation
        fields = "__all__"
