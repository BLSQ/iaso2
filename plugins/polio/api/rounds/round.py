from django.db.models.expressions import Subquery
from django.db.transaction import atomic
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response

from hat.menupermissions import models as permission
from iaso.api.common import HasPermission, ModelViewSet
from plugins.polio.api.shared_serializers import (
    GroupSerializer,
    RoundDateHistoryEntryForRoundSerializer,
)
from plugins.polio.models import ReasonForDelay, Round, RoundDateHistoryEntry, RoundScope, Campaign
from plugins.polio.preparedness.summary import set_preparedness_cache_for_round


class RoundScopeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoundScope
        fields = ["group", "vaccine"]

    group = GroupSerializer()


class RoundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Round
        fields = "__all__"

    scopes = RoundScopeSerializer(many=True, required=False)
    datelogs = RoundDateHistoryEntryForRoundSerializer(many=True, required=False)
    districts_count_calculated = serializers.IntegerField(read_only=True)

    # Vaccines from real scopes, from property, separated by ,
    vaccine_names = serializers.CharField(read_only=True)
    vaccine_names_extended = serializers.SerializerMethodField(read_only=True)

    def get_vaccine_names_extended(self, obj):
        return obj.vaccine_names_extended

    @atomic
    def create(self, validated_data):
        request = self.context.get("request")
        user = request.user
        started_at = validated_data.get("started_at", None)
        ended_at = validated_data.get("ended_at", None)
        datelogs = validated_data.pop("datelogs", None)
        if datelogs:
            raise serializers.ValidationError({"datelogs": "Cannot have modification history for new round"})
        round = Round.objects.create(**validated_data)
        round.add_chronogram()
        if started_at is not None or ended_at is not None:
            reason_for_delay = ReasonForDelay.objects.filter(key_name="INITIAL_DATA").first()
            datelog = RoundDateHistoryEntry.objects.create(
                round=round, reason_for_delay=reason_for_delay, modified_by=user
            )
            if started_at is not None:
                datelog.started_at = started_at
            if ended_at is not None:
                datelog.ended_at = ended_at
            datelog.save()
        return round

    @atomic
    def update(self, instance, validated_data):
        request = self.context.get("request")
        user = request.user
        account = user.iaso_profile.account
        updated_datelogs = validated_data.pop("datelogs", [])

        has_datelog = instance.datelogs.count() > 0
        if updated_datelogs:
            new_datelog = updated_datelogs[-1]
            datelog = None
            if has_datelog:
                last_entry = instance.datelogs.order_by("-created_at").first()
                # if instance.datelogs.count() >= len(updated_datelogs) it means there was an update that was missed between input and confirmation
                # This could lead to errors in the log with the previous_started_at and previous_ended_at fields
                if len(updated_datelogs) >= instance.datelogs.count():
                    new_datelog["previous_started_at"] = last_entry.started_at
                    new_datelog["previous_ended_at"] = last_entry.ended_at
                if (
                    new_datelog["reason_for_delay"].id != last_entry.reason_for_delay.id
                    or new_datelog["started_at"] != last_entry.started_at
                    or new_datelog["ended_at"] != last_entry.ended_at
                ) and new_datelog[
                    "reason_for_delay"
                ].key_name != "INITIAL_DATA":  # INITAL_DATA should prolly be put in a const somewhere
                    datelog = RoundDateHistoryEntry.objects.create(round=instance, modified_by=user)
            else:
                try:
                    reason_for_delay = ReasonForDelay.objects.filter(account=account).get(key_name="INITIAL_DATA")
                except ReasonForDelay.DoesNotExist:
                    # Fallback on first reason available for account
                    reason_for_delay = ReasonForDelay.filter(account=account).first()
                datelog = RoundDateHistoryEntry.objects.create(
                    round=instance, reason_for_delay=reason_for_delay, modified_by=user
                )
            if datelog is not None:
                # Replace instance with key_name to avoid validation error
                # Because the serializer is nested, and data is converted at every level of nesting
                # datelog["reason_for_delay"] is the ReasonForDelay instance, and not the  key_name that was passed by the front-end
                # So we have to extract the key_name from the instance and re-pass it to the serializer, otherwise we get an error
                datelog_serializer = RoundDateHistoryEntryForRoundSerializer(
                    instance=datelog,
                    data={**new_datelog, "reason_for_delay": new_datelog["reason_for_delay"].key_name},
                    context=self.context,
                )
                datelog_serializer.is_valid(raise_exception=True)
                datelog_instance = datelog_serializer.save()
                instance.datelogs.add(datelog_instance)

        round = super().update(instance, validated_data)
        # update the preparedness cache in case we touched the spreadsheet url
        set_preparedness_cache_for_round(round)
        return round


class LqasDistrictsUpdateSerializer(serializers.Serializer):
    number = serializers.IntegerField(required=True)
    lqas_district_failing = serializers.IntegerField(required=True)
    lqas_district_passing = serializers.IntegerField(required=True)
    obr_name = serializers.CharField(required=True)

    def update(self, instance, validated_data):
        # We save None i.o 0 to avoid breaking powerBi dashboards
        instance.lqas_district_passing = (
            validated_data["lqas_district_passing"] if validated_data["lqas_district_passing"] > 0 else None
        )
        # We save None i.o 0 to avoid breaking powerBi dashboards
        instance.lqas_district_failing = (
            validated_data["lqas_district_failing"] if validated_data["lqas_district_failing"] > 0 else None
        )
        instance.save()
        return instance


@swagger_auto_schema(tags=["rounds"], request_body=LqasDistrictsUpdateSerializer)
class RoundViewSet(ModelViewSet):
    # Patch should be in the list to allow updatelqasfields to work
    http_method_names = ["patch"]
    permission_classes = [HasPermission(permission.POLIO, permission.POLIO_CONFIG)]  # type: ignore
    serializer_class = RoundSerializer
    model = Round

    def partial_update(self):
        """Don't PATCH this way, it will not do anything
        Overriding to prevent patching the whole round which is error prone, due to nested fields among others.
        """
        pass

    # Endpoint used to update lqas passed and failed fields by OpenHexa pipeline
    @action(detail=False, methods=["patch"], serializer_class=LqasDistrictsUpdateSerializer)
    def updatelqasfields(self, request):
        round_number = request.data.get("number", None)
        obr_name = request.data.get("obr_name", None)
        user = self.request.user
        if obr_name is None:
            raise serializers.ValidationError({"obr_name": "This field is required"})
        if round_number is None:
            raise serializers.ValidationError({"round_number": "This field is required"})
        try:
            campaigns_for_user = Campaign.objects.filter_for_user(user)
            round_instance = Round.objects.filter(
                campaign__obr_name__in=Subquery(campaigns_for_user.values("obr_name"))
            )
            round_instance = round_instance.get(campaign__obr_name=obr_name, number=round_number)
            serializer = LqasDistrictsUpdateSerializer(data=request.data, context={"request": request}, partial=True)
            serializer.is_valid(raise_exception=True)
            res = serializer.update(round_instance, serializer.validated_data)
            serialized_data = RoundSerializer(res).data
            return Response(serialized_data)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)
