import json
from datetime import datetime
from tempfile import NamedTemporaryFile
from time import gmtime, strftime
from typing import Any, List, Union

from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.db.models import Max, Min, Prefetch, Q
from django.db.models.expressions import RawSQL
from django.db.models.query import QuerySet
from django.db.transaction import atomic
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.timezone import make_aware, now
from django.utils.translation import gettext as _
from django_filters.rest_framework import DjangoFilterBackend  # type: ignore
from gspread.exceptions import APIError  # type: ignore
from rest_framework import filters, permissions, serializers, status
from rest_framework.decorators import action
from rest_framework.fields import Field
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.validators import UniqueValidator

from hat.api.export_utils import Echo, iter_items
from iaso.api.common import (
    CONTENT_TYPE_CSV,
    CONTENT_TYPE_XLSX,
    Custom403Exception,
    CustomFilterBackend,
    DeletionFilterBackend,
    ModelViewSet,
)
from iaso.models import Group, OrgUnit
from plugins.polio.api.campaigns.campaigns_log import log_campaign_modification, serialize_campaign
from plugins.polio.api.campaigns.vaccine_authorization_missing_email import (
    missing_vaccine_authorization_for_campaign_email_alert,
)
from plugins.polio.api.common import CACHE_VERSION
from plugins.polio.api.rounds.round import RoundScopeSerializer, RoundSerializer
from plugins.polio.api.shared_serializers import GroupSerializer, OrgUnitSerializer
from plugins.polio.export_utils import generate_xlsx_campaigns_calendar, xlsx_file_name
from plugins.polio.models import (
    Campaign,
    CampaignGroup,
    CampaignScope,
    CampaignType,
    CountryUsersGroup,
    Round,
    RoundScope,
    SpreadSheetImport,
    VaccineAuthorization,
)
from plugins.polio.models.base import SubActivity, SubActivityScope
from plugins.polio.preparedness.calculator import get_preparedness_score
from plugins.polio.preparedness.parser import InvalidFormatError, get_preparedness
from plugins.polio.preparedness.spreadsheet_manager import Campaign, generate_spreadsheet_for_campaign
from plugins.polio.preparedness.summary import preparedness_summary


# Don't display the url for Anonymous users
class RoundAnonymousSerializer(RoundSerializer):
    class Meta:
        model = Round
        exclude = ["preparedness_spreadsheet_url"]


class CampaignScopeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampaignScope
        fields = ["group", "vaccine"]

    group = GroupSerializer()


class CurrentAccountDefault:
    """
    May be applied as a `default=...` value on a serializer field.
    Returns the current user's account.
    """

    requires_context = True

    def __call__(self, serializer_field):
        return serializer_field.context["request"].user.iaso_profile.account_id


def check_total_doses_requested(vaccine_authorization, nOPV2_rounds, current_campaign):
    """
    Check if the total doses requested per round in a campaign is not superior to the allowed doses in the vaccine authorization.
    It also emails the nopv2 vaccine team about it.
    """
    if vaccine_authorization and vaccine_authorization.quantity is not None:
        campaigns = Campaign.objects.filter(country=vaccine_authorization.country, deleted_at__isnull=True).exclude(
            pk=current_campaign.pk
        )
        total_doses_requested_for_campaigns = 0
        campaigns_rounds = [c_round for c_round in Round.objects.filter(campaign__in=campaigns)]

        existing_nopv2_rounds = []
        for r in campaigns_rounds:
            if "nOPV2" in r.vaccine_names:
                existing_nopv2_rounds.append(r)

        for r in existing_nopv2_rounds:
            if r.started_at and r.doses_requested:
                if vaccine_authorization.start_date <= r.started_at <= vaccine_authorization.expiration_date:
                    total_doses_requested_for_campaigns += r.doses_requested

        total_doses_requested = 0
        for c_round in nOPV2_rounds:
            if c_round.doses_requested is not None:
                if c_round.started_at >= vaccine_authorization.start_date <= vaccine_authorization.expiration_date:
                    total_doses_requested += c_round.doses_requested

        if total_doses_requested + total_doses_requested_for_campaigns > vaccine_authorization.quantity:
            message = f"The total of doses requested {total_doses_requested} is superior to the autorized doses for this campaign {vaccine_authorization.quantity}."
            if total_doses_requested_for_campaigns > 0:
                message = f"The total of doses requested {total_doses_requested} and the aggregation of all previous requested doses {total_doses_requested_for_campaigns} are superior to the autorized doses for this campaign {vaccine_authorization.quantity}."
            raise Custom403Exception(message)


class CampaignTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampaignType
        fields = ["id", "name", "slug"]


class CampaignSerializer(serializers.ModelSerializer):
    rounds = RoundSerializer(many=True, required=False)
    org_unit: Field = OrgUnitSerializer(source="initial_org_unit", read_only=True)
    top_level_org_unit_name: Field = serializers.SlugRelatedField(source="country", slug_field="name", read_only=True)
    top_level_org_unit_id: Field = serializers.SlugRelatedField(source="country", slug_field="id", read_only=True)
    general_status = serializers.SerializerMethodField()
    grouped_campaigns = serializers.PrimaryKeyRelatedField(
        many=True, queryset=CampaignGroup.objects.all(), required=False
    )
    # Account is filed per default the one of the connected user that update it
    account: Field = serializers.PrimaryKeyRelatedField(default=CurrentAccountDefault(), read_only=True)
    has_data_in_budget_tool = serializers.SerializerMethodField(read_only=True)
    campaign_types = serializers.PrimaryKeyRelatedField(many=True, queryset=CampaignType.objects.all(), required=False)
    # Vaccines with real scope
    vaccines = serializers.SerializerMethodField(read_only=True)
    single_vaccines = serializers.SerializerMethodField(read_only=True)

    def get_vaccines(self, obj):
        if obj.vaccines_extended_list:
            return ",".join(obj.vaccines_extended_list)
        return ""

    def get_single_vaccines(self, obj):
        return obj.single_vaccines_extended

    def get_top_level_org_unit_name(self, campaign):
        if campaign.country:
            return campaign.country.name
        return ""

    def get_top_level_org_unit_id(self, campaign):
        if campaign.country:
            return campaign.country.id
        return ""

    def get_general_status(self, campaign):
        now_utc = timezone.now().date()
        ordered_rounds = list(campaign.rounds.all())
        ordered_rounds.sort(key=lambda x: x.number, reverse=True)
        for round in ordered_rounds:
            if round.ended_at and now_utc > round.ended_at:
                return _("Round {} ended").format(round.number)
            elif round.started_at and now_utc >= round.started_at:
                return _("Round {} started").format(round.number)
        return _("Preparing")

    def get_has_data_in_budget_tool(self, campaign):
        return campaign.budget_steps.count() > 0

    scopes = CampaignScopeSerializer(many=True, required=False)

    obr_name = serializers.CharField(validators=[UniqueValidator(queryset=Campaign.objects.all())])

    @atomic
    def create(self, validated_data):
        grouped_campaigns = validated_data.pop("grouped_campaigns", [])
        rounds = validated_data.pop("rounds", [])
        campaign_types = validated_data.pop("campaign_types", [])
        initial_org_unit = validated_data.get("initial_org_unit")
        obr_name = validated_data["obr_name"]
        account = self.context["request"].user.iaso_profile.account

        campaign_scopes = validated_data.pop("scopes", [])
        campaign = Campaign.objects.create(
            # there seems a bug in DRF the account is not in validated data, when not using HiddenField
            account_id=self.context["request"].user.iaso_profile.account_id,
            **validated_data,
        )

        campaign.grouped_campaigns.set(grouped_campaigns)

        # noinspection DuplicatedCode
        for scope in campaign_scopes:
            vaccine = scope.get("vaccine", "")
            org_units = scope.get("group", {}).get("org_units")
            scope, created = campaign.scopes.get_or_create(vaccine=vaccine)
            source_version_id = None
            name = f"scope {scope.id} for campaign {campaign.obr_name}" + (f" - {vaccine}" if vaccine else "")
            if org_units:
                source_version_ids = set([ou.version_id for ou in org_units])
                if len(source_version_ids) != 1:
                    raise serializers.ValidationError("All orgunit should be in the same source version")
                source_version_id = list(source_version_ids)[0]
            if not scope.group:
                scope.group = Group.objects.create(name=name, source_version_id=source_version_id)
            else:
                scope.group.source_version_id = source_version_id
                scope.group.name = name
                scope.group.save()

            scope.group.org_units.set(org_units)

        if campaign_types:
            campaign.campaign_types.set(campaign_types)
        else:  # if no campaign_types are given, we assume it's a polio campaign
            polio_type = CampaignType.objects.get(name=CampaignType.POLIO)
            campaign.campaign_types.set([polio_type])

        for round_data in rounds:
            scopes = round_data.pop("scopes", [])
            round_serializer = RoundSerializer(data={**round_data, "campaign": campaign.id}, context=self.context)
            round_serializer.is_valid(raise_exception=True)
            round = round_serializer.save()

            for scope in scopes:
                vaccine = scope.get("vaccine", "")
                org_units = scope.get("group", {}).get("org_units")
                source_version_id = None
                if org_units:
                    source_version_ids = set([ou.version_id for ou in org_units])
                    if len(source_version_ids) != 1:
                        raise serializers.ValidationError("All orgunit should be in the same source version")
                    source_version_id = list(source_version_ids)[0]
                scope, created = round.scopes.get_or_create(vaccine=vaccine)
                name = f"scope {scope.id} for round {round.number} campaign {campaign.obr_name}" + (
                    f" - {vaccine}" if vaccine else ""
                )
                if not scope.group:
                    scope.group = Group.objects.create(name=name)
                else:
                    scope.group.source_version_id = source_version_id
                    scope.group.name = name
                    scope.group.save()

                scope.group.org_units.set(org_units)

        campaign.update_geojson_field()
        campaign.save()
        log_campaign_modification(campaign, None, self.context["request"].user)

        # check if the quantity of the vaccines requested is not superior to the authorized vaccine quantity
        c_rounds = [r for r in campaign.rounds.all()]
        nOPV2_rounds = []
        for r in c_rounds:
            if "nOPV2" in r.vaccine_names:
                nOPV2_rounds.append(r)

        if initial_org_unit and len(nOPV2_rounds) > 0:
            try:
                initial_org_unit = OrgUnit.objects.get(pk=initial_org_unit.pk)
                vaccine_authorization = VaccineAuthorization.objects.filter(
                    country=initial_org_unit, status="VALIDATED", account=account, deleted_at__isnull=True
                )
                if vaccine_authorization:
                    check_total_doses_requested(vaccine_authorization[0], nOPV2_rounds, campaign)
                else:
                    missing_vaccine_authorization_for_campaign_email_alert(
                        obr_name, validated_data["initial_org_unit"], account
                    )
            except OrgUnit.DoesNotExist:
                raise Custom403Exception("error:" "Org unit does not exists.")

        return campaign

    @atomic
    def update(self, instance: Campaign, validated_data):
        old_campaign_dump = serialize_campaign(instance)
        campaign_scopes = validated_data.pop("scopes", [])
        rounds = validated_data.pop("rounds", [])
        initial_org_unit = validated_data.get("initial_org_unit")
        account = self.context["request"].user.iaso_profile.account
        separate_scopes_per_round = validated_data.get("separate_scopes_per_round", instance.separate_scopes_per_round)
        switch_to_scope_per_round = separate_scopes_per_round and not instance.separate_scopes_per_round
        switch_to_scope_per_campaign = not separate_scopes_per_round and instance.separate_scopes_per_round
        keep_scope_per_round = separate_scopes_per_round and instance.separate_scopes_per_round
        keep_scope_per_campaign = not separate_scopes_per_round and not instance.separate_scopes_per_round

        if switch_to_scope_per_round and instance.scopes.exists():
            instance.scopes.all().delete()

        if switch_to_scope_per_campaign or keep_scope_per_campaign:
            for scope in campaign_scopes:
                vaccine = scope.get("vaccine", "")
                org_units = scope.get("group", {}).get("org_units")
                scope, created = instance.scopes.get_or_create(vaccine=vaccine)
                source_version_id = None
                name = f"scope for campaign {instance.obr_name} - {vaccine or ''}"
                if org_units:
                    source_version_ids = set([ou.version_id for ou in org_units])
                    if len(source_version_ids) != 1:
                        raise serializers.ValidationError("All orgunit should be in the same source version")
                    source_version_id = list(source_version_ids)[0]
                if not scope.group:
                    scope.group = Group.objects.create(name=name, source_version_id=source_version_id)
                else:
                    scope.group.source_version_id = source_version_id
                    scope.group.name = name
                    scope.group.save()

                scope.group.org_units.set(org_units)

        round_instances = []
        # find existing round either by id or number
        # Fixme this is not a partial update because of the dfault
        for round_data in rounds:
            round = None
            if round_data.get("id"):
                round_id = round_data["id"]
                round = Round.objects.get(pk=round_id)
                if round.campaign != instance:
                    raise serializers.ValidationError({"rounds": "round is attached to a different campaign"})
            elif round_data.get("number", None) is not None:
                try:
                    round = instance.rounds.get(number=round_data.get("number"))
                except Round.DoesNotExist:
                    pass
            # we pop the campaign since we use the set afterward which will also remove the deleted one
            round_data.pop("campaign", None)
            scopes = round_data.pop("scopes", [])

            # Replace ReasonForDelay instance with key_name to avoid type error when calling is_valid
            # Because the serializer is nested, and data is converted at every level of nesting
            # datelog["reason_for_delay"] is the ReasonForDelay instance, and not the  key_name that was passed by the front-end
            # So we have to extract the key_name from the instance and re-pass it to the serializer, otherwise we get an error
            round_datelogs = round_data.pop("datelogs", [])
            datelogs_with_pk = [
                {**datelog, "reason_for_delay": datelog["reason_for_delay"].key_name} for datelog in round_datelogs
            ]
            round_data["datelogs"] = datelogs_with_pk

            # At this point `round_data` has already been validated and deserialized to complex Django types.
            # But it will still be passed to `RoundSerializer.data` as if it were native Python datatypes.
            # So, we convert it back to a native datatype to prevent `RoundSerializer` to raise an error:
            # "Incorrect type. Expected pk value, received BudgetProcess."…
            budget_process = round_data.pop("budget_process", None)
            round_data["budget_process"] = budget_process.pk if budget_process else None

            round_serializer = RoundSerializer(instance=round, data=round_data, context=self.context)
            round_serializer.is_valid(raise_exception=True)
            round_instance = round_serializer.save()
            round_instances.append(round_instance)
            round_datelogs = []
            if switch_to_scope_per_campaign and round.scopes.exists():
                round.scopes.all().delete()
            if switch_to_scope_per_round or keep_scope_per_round:
                for scope in scopes:
                    vaccine = scope.get("vaccine", "")
                    org_units = scope.get("group", {}).get("org_units")
                    source_version_id = None
                    if org_units:
                        source_version_ids = set([ou.version_id for ou in org_units])
                        if len(source_version_ids) != 1:
                            raise serializers.ValidationError("All orgunit should be in the same source version")
                        source_version_id = list(source_version_ids)[0]
                    name = f"scope for round {round_instance.number} campaign {instance.obr_name}" + (
                        f" - {vaccine}" if vaccine else ""
                    )
                    scope, created = round_instance.scopes.get_or_create(vaccine=vaccine)
                    if not scope.group:
                        scope.group = Group.objects.create(name=name)
                    else:
                        scope.group.source_version_id = source_version_id
                        scope.group.name = name
                        scope.group.save()

                    scope.group.org_units.set(org_units)

        submitted_round_ids = set([r.id for r in round_instances])
        current_round_ids = set(instance.rounds.values_list("id", flat=True))

        # When some rounds need to be deleted, the payload contains only the rounds to keep.
        # So we have to detect if somebody wants to delete a round to prevent deletion of
        # rounds linked to budget processes.
        has_rounds_to_delete = round_instances and len(current_round_ids) > len(submitted_round_ids)
        if has_rounds_to_delete:
            rounds_to_delete = instance.rounds.exclude(id__in=submitted_round_ids)
            if rounds_to_delete.filter(budget_process__isnull=False).exists():
                raise serializers.ValidationError("Cannot delete a round linked to a budget process.")
            else:
                rounds_to_delete.delete()

        instance.rounds.set(round_instances)

        # We have to detect new rounds manually because of the way rounds are associated to the campaign.
        new_rounds_ids = submitted_round_ids - current_round_ids
        if new_rounds_ids:
            for round in instance.rounds.filter(id__in=new_rounds_ids):
                round.add_chronogram()

        campaign = super().update(instance, validated_data)
        campaign.update_geojson_field()
        campaign.save()

        # check if the quantity of the vaccines requested is not superior to the authorized vaccine quantity
        c_rounds = [r for r in campaign.rounds.all()]
        nOPV2_rounds = []
        for r in c_rounds:
            if "nOPV2" in r.vaccine_names:
                nOPV2_rounds.append(r)
        if initial_org_unit and len(nOPV2_rounds) > 0:
            try:
                initial_org_unit = OrgUnit.objects.get(pk=initial_org_unit.pk)
                vaccine_authorization = VaccineAuthorization.objects.filter(
                    country=initial_org_unit, status="VALIDATED", account=account, deleted_at__isnull=True
                )
                if vaccine_authorization:
                    check_total_doses_requested(vaccine_authorization[0], nOPV2_rounds, campaign)
            except OrgUnit.DoesNotExist:
                raise Custom403Exception("error:" "Org unit does not exists.")

        log_campaign_modification(campaign, old_campaign_dump, self.context["request"].user)
        return campaign

    class Meta:
        model = Campaign
        # TODO in the future specify the fields that need to be returned so we can remove the deprecated fields
        # fields = "__all__"
        exclude = ["geojson"]

        read_only_fields = ["creation_email_send_at", "group"]


class ListCampaignSerializer(CampaignSerializer):
    """This serializer contains juste enough data for the List view in the web ui"""

    class NestedListRoundSerializer(RoundSerializer):
        class Meta:
            model = Round
            fields = [
                "id",
                "number",
                "started_at",
                "ended_at",
            ]

    rounds = NestedListRoundSerializer(many=True, required=False)

    campaign_types = CampaignTypeSerializer(many=True, required=False)

    class Meta:
        model = Campaign
        fields = [
            "id",
            "epid",
            "obr_name",
            "account",
            "cvdpv2_notified_at",
            "top_level_org_unit_name",
            "top_level_org_unit_id",
            "rounds",
            "general_status",
            "grouped_campaigns",
            "campaign_types",
            "is_test",
            "is_preventive",
        ]
        read_only_fields = fields


class AnonymousCampaignSerializer(CampaignSerializer):
    rounds = RoundAnonymousSerializer(many=True)
    campaign_types = CampaignTypeSerializer(many=True, required=False)

    class Meta:
        model = Campaign
        fields = [
            "id",
            "epid",
            "obr_name",
            "gpei_coordinator",
            "gpei_email",
            "description",
            "initial_org_unit",
            "creation_email_send_at",
            "onset_at",
            "cvdpv2_notified_at",
            "pv_notified_at",
            "pv2_notified_at",
            "virus",
            "scopes",
            "vaccines",
            "detection_status",
            "detection_responsible",
            "detection_first_draft_submitted_at",
            "risk_assessment_status",
            "risk_assessment_responsible",
            "investigation_at",
            "risk_assessment_first_draft_submitted_at",
            "risk_assessment_rrt_oprtt_approval_at",
            "ag_nopv_group_met_at",
            "dg_authorized_at",
            "verification_score",
            "budget_status",
            "who_disbursed_to_co_at",
            "who_disbursed_to_moh_at",
            "unicef_disbursed_to_co_at",
            "unicef_disbursed_to_moh_at",
            "no_regret_fund_amount",
            "payment_mode",
            "rounds",
            "created_at",
            "updated_at",
            "district_count",
            "top_level_org_unit_name",
            "top_level_org_unit_id",
            "is_preventive",
            "account",
            "outbreak_declaration_date",
            "campaign_types",
        ]
        read_only_fields = fields


class SmallCampaignSerializer(CampaignSerializer):
    campaign_types = CampaignTypeSerializer(many=True, required=False)

    class Meta:
        model = Campaign
        # TODO: refactor to avoid duplication with AnonymousCampaignSerializer?
        fields = [
            "id",
            "epid",
            "obr_name",
            "gpei_coordinator",
            "gpei_email",
            "description",
            "initial_org_unit",
            "creation_email_send_at",
            "onset_at",
            "cvdpv2_notified_at",
            "pv_notified_at",
            "pv2_notified_at",
            "virus",
            "vaccines",
            "detection_status",
            "detection_responsible",
            "detection_first_draft_submitted_at",
            "risk_assessment_status",
            "risk_assessment_responsible",
            "investigation_at",
            "risk_assessment_first_draft_submitted_at",
            "risk_assessment_rrt_oprtt_approval_at",
            "ag_nopv_group_met_at",
            "dg_authorized_at",
            "verification_score",
            "budget_status",
            "who_disbursed_to_co_at",
            "who_disbursed_to_moh_at",
            "unicef_disbursed_to_co_at",
            "unicef_disbursed_to_moh_at",
            "no_regret_fund_amount",
            "payment_mode",
            "created_at",
            "updated_at",
            "district_count",
            "top_level_org_unit_name",
            "top_level_org_unit_id",
            "is_preventive",
            "account",
            "outbreak_declaration_date",
            "campaign_types",
        ]
        read_only_fields = fields


class CalendarCampaignSerializer(CampaignSerializer):
    """This serializer contains juste enough data for the Calendar view in the web ui. Read only.
    Used by both anonymous and non-anonymous user"""

    class NestedSubactivitySerializer(serializers.ModelSerializer):
        class NestedScopeSerializer(serializers.ModelSerializer):
            class NestedGroupSerializer(GroupSerializer):
                class Meta:
                    model = Group
                    fields = ["id"]

            class Meta:
                model = SubActivityScope
                fields = ["group", "vaccine"]

            group = NestedGroupSerializer()

        scopes = NestedScopeSerializer(many=True)
        round_number = serializers.IntegerField(source="round.number")

        class Meta:
            model = SubActivity
            fields = ["name", "start_date", "end_date", "scopes", "id", "vaccine_names", "round_number"]

    class NestedListRoundSerializer(RoundSerializer):
        class NestedScopeSerializer(RoundScopeSerializer):
            class NestedGroupSerializer(GroupSerializer):
                class Meta:
                    model = Group
                    fields = ["id"]

            class Meta:
                model = RoundScope
                fields = ["group", "vaccine"]

            group = NestedGroupSerializer()

        class Meta:
            model = Round
            fields = ["id", "number", "started_at", "ended_at", "scopes", "vaccine_names", "target_population"]

        def to_representation(self, instance):
            # Skip test rounds
            if instance.is_test:
                return None
            return super().to_representation(instance)

    class NestedScopeSerializer(CampaignScopeSerializer):
        class NestedGroupSerializer(GroupSerializer):
            class Meta:
                model = Group
                fields = ["id"]

        class Meta:
            model = CampaignScope
            fields = ["group", "vaccine"]

        group = NestedGroupSerializer()

    rounds = NestedListRoundSerializer(many=True, required=False)
    scopes = NestedScopeSerializer(many=True, required=False)
    campaign_types = CampaignTypeSerializer(many=True, required=False)
    sub_activities = serializers.SerializerMethodField()

    def get_sub_activities(self, campaign):
        sub_activities = SubActivity.objects.filter(round__campaign=campaign)
        return self.NestedSubactivitySerializer(sub_activities, many=True, context=self.context).data

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Filter out None values from rounds (the test rounds we skipped)
        data["rounds"] = [r for r in data["rounds"] if r is not None]
        return data

    class Meta:
        model = Campaign
        fields = [
            "id",
            "epid",
            "obr_name",
            "account",
            "top_level_org_unit_name",
            "top_level_org_unit_id",
            "rounds",
            "sub_activities",
            "is_preventive",
            "general_status",
            "grouped_campaigns",
            "separate_scopes_per_round",
            "scopes",
            # displayed in RoundPopper
            # To deprecate in front-end code as it doesn't have subactivities
            "vaccines",
            "single_vaccines",
            "campaign_types",
            "description",
            "is_test",
        ]
        read_only_fields = fields


def preparedness_from_url(spreadsheet_url, force_refresh=False):
    try:
        if force_refresh:
            ssi = SpreadSheetImport.create_for_url(spreadsheet_url)
        else:
            ssi = SpreadSheetImport.last_for_url(spreadsheet_url)
        if not ssi:
            return {}

        cs = ssi.cached_spreadsheet
        r = {}
        preparedness_data = get_preparedness(cs)
        r.update(preparedness_data)
        r["title"] = cs.title
        r["created_at"] = ssi.created_at
        r.update(get_preparedness_score(preparedness_data))
        r.update(preparedness_summary(preparedness_data))
        return r
    except InvalidFormatError as e:
        raise serializers.ValidationError(e.args[0])
    except APIError as e:
        raise serializers.ValidationError(e.args[0].get("message"))


class PreparednessPreviewSerializer(serializers.Serializer):
    google_sheet_url = serializers.URLField()

    def validate(self, attrs):
        spreadsheet_url = attrs.get("google_sheet_url")
        return preparedness_from_url(spreadsheet_url, force_refresh=True)

    def to_representation(self, instance):
        return instance


def get_current_preparedness(campaign, roundNumber):
    try:
        round = campaign.rounds.get(number=roundNumber)
    except Round.DoesNotExist:
        return {"details": f"No round {roundNumber} on this campaign"}

    if not round.preparedness_spreadsheet_url:
        return {}
    spreadsheet_url = round.preparedness_spreadsheet_url
    return preparedness_from_url(spreadsheet_url)


class CampaignPreparednessSpreadsheetSerializer(serializers.Serializer):
    """Serializer used to CREATE Preparedness spreadsheet from template"""

    campaign = serializers.PrimaryKeyRelatedField(queryset=Campaign.objects.all(), write_only=True)
    round_number = serializers.IntegerField(required=False)
    url = serializers.URLField(read_only=True)

    def create(self, validated_data):
        campaign = validated_data.get("campaign")
        round_number = validated_data.get("round_number")

        spreadsheet = generate_spreadsheet_for_campaign(campaign, round_number)

        return {"url": spreadsheet.url}


class CampaignViewSet(ModelViewSet):
    """Main endpoint for campaign.

    GET (Anonymously too)
    POST
    PATCH
    See swagger for Parameters
    """

    results_key = "campaigns"
    remove_results_key_if_paginated = True
    filter_backends = [
        filters.OrderingFilter,
        DjangoFilterBackend,
        CustomFilterBackend,
        DeletionFilterBackend,
    ]

    ordering_fields = [
        "obr_name",
        "cvdpv2_notified_at",
        "detection_status",
        "first_round_started_at",
        "last_round_started_at",
        "country__name",
    ]
    filterset_fields = {
        "country__name": ["exact"],
        "country__id": ["in"],
        "grouped_campaigns__id": ["in", "exact"],
        "obr_name": ["exact", "contains"],
        "cvdpv2_notified_at": ["gte", "lte", "range"],
        "created_at": ["gte", "lte", "range"],
        "rounds__started_at": ["gte", "lte", "range"],
    }

    # We allow anonymous read access for the embeddable calendar map view
    # in this case we use a restricted serializer with less field
    # notably not the url that we want to remain private.
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    export_filename = "campaigns_list_{date}.csv"
    use_field_order = False

    def get_serializer_class(self):
        if self.request.user.is_authenticated:
            if self.request.query_params.get("fieldset") == "list" and self.request.method in permissions.SAFE_METHODS:
                return ListCampaignSerializer
            if (
                self.request.query_params.get("fieldset") == "calendar"
                and self.request.method in permissions.SAFE_METHODS
            ):
                return CalendarCampaignSerializer

            return CampaignSerializer
        else:
            if (
                self.request.query_params.get("fieldset") == "calendar"
                and self.request.method in permissions.SAFE_METHODS
            ):
                return CalendarCampaignSerializer
            return AnonymousCampaignSerializer

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        if self.action in ("update", "partial_update", "retrieve", "destroy"):
            return queryset
        campaign_category = self.request.query_params.get("campaign_category")
        campaign_groups = self.request.query_params.get("campaign_groups")
        show_test = self.request.query_params.get("show_test", "false")
        org_unit_groups = self.request.query_params.get("org_unit_groups")
        campaign_types = self.request.query_params.get("campaign_types")
        campaigns = queryset
        if show_test == "false":
            campaigns = campaigns.filter(is_test=False)
        if campaign_category == "preventive":
            campaigns = campaigns.filter(is_preventive=True)
        if campaign_category == "test":
            campaigns = campaigns.filter(is_test=True)
        if campaign_category == "regular":
            campaigns = campaigns.filter(is_preventive=False).filter(is_test=False)
        if campaign_groups:
            campaigns = campaigns.filter(grouped_campaigns__in=campaign_groups.split(","))
        if org_unit_groups:
            campaigns = campaigns.filter(country__groups__in=org_unit_groups.split(","))
        if campaign_types:
            campaign_types_list = campaign_types.split(",")
            if all(item.isdigit() for item in campaign_types_list):
                campaigns = campaigns.filter(campaign_types__id__in=campaign_types_list)
            else:
                campaigns = campaigns.filter(campaign_types__slug__in=campaign_types_list)
        org_units_id_only_qs = OrgUnit.objects.only("id", "name")
        country_prefetch = Prefetch("country", queryset=org_units_id_only_qs)
        scopes_group_org_units_prefetch = Prefetch("scopes__group__org_units", queryset=org_units_id_only_qs)
        rounds_scopes_group_org_units_prefetch = Prefetch(
            "rounds__scopes__group__org_units", queryset=org_units_id_only_qs
        )
        campaigns = (
            campaigns.prefetch_related(country_prefetch)
            .prefetch_related("grouped_campaigns")
            .prefetch_related("scopes")
            .prefetch_related("scopes__group")
            .prefetch_related(scopes_group_org_units_prefetch)
            .prefetch_related("rounds")
            .prefetch_related("rounds__datelogs")
            .prefetch_related("rounds__datelogs__modified_by")
            .prefetch_related("rounds__scopes")
            .prefetch_related("rounds__scopes__group")
            .prefetch_related(rounds_scopes_group_org_units_prefetch)
        )
        return campaigns.distinct()

    def get_queryset(self):
        user = self.request.user
        campaigns = Campaign.objects.all()

        # used for Ordering
        campaigns = campaigns.annotate(last_round_started_at=Max("rounds__started_at"))
        campaigns = campaigns.annotate(first_round_started_at=Min("rounds__started_at"))

        campaigns = campaigns.filter_for_user(user)
        if not self.request.user.is_authenticated:
            # For this endpoint since it's available anonymously we allow all user to list the campaigns
            # and to additionally filter on the account_id
            # In the future we may want to make the account_id parameter mandatory.
            account_id = self.request.query_params.get("account_id", None)
            if account_id is not None:
                campaigns = campaigns.filter(account_id=account_id)

        return campaigns

    @action(detail=False, methods=["GET"], serializer_class=CampaignTypeSerializer)
    def available_campaign_types(self, request):
        campaign_types = CampaignType.objects.all()
        serializer = CampaignTypeSerializer(campaign_types, many=True)
        return Response(serializer.data)

    @action(methods=["POST"], detail=False, serializer_class=PreparednessPreviewSerializer)
    def preview_preparedness(self, request, **kwargs):
        serializer = PreparednessPreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)

    @action(methods=["GET"], detail=True, serializer_class=serializers.Serializer)
    def preparedness(self, request, **kwargs):
        campaign = self.get_object()
        roundNumber = request.query_params.get("round", "")
        return Response(get_current_preparedness(campaign, roundNumber))

    @action(methods=["GET"], detail=False, serializer_class=None)
    def create_calendar_xlsx_sheet(self, request, **kwargs):
        current_date = request.query_params.get("currentDate")
        current_year = self.get_year(current_date)

        params = request.query_params
        calendar_data = self.get_calendar_data(current_year, params)
        filename = xlsx_file_name("calendar", params)
        xlsx_file = generate_xlsx_campaigns_calendar(filename, calendar_data)

        with NamedTemporaryFile() as tmp:
            xlsx_file.save(tmp.name)
            tmp.seek(0)
            stream = tmp.read()

        response = HttpResponse(stream, content_type=CONTENT_TYPE_XLSX)
        response["Content-Disposition"] = "attachment; filename=%s" % filename + ".xlsx"
        return response

    @action(methods=["GET"], detail=False, serializer_class=None)
    def create_all_rounds_scopes_csv(self, request, **kwargs):
        """
        It generates a csv export file with all round's related informations

            parameters:
                self: a self
                roundStartFrom: a date
                roundStartTo: a date
            returns:
                it generates a csv file export
        """
        round_start_from = request.GET.get("roundStartFrom")
        round_start_to = request.GET.get("roundStartTo")
        current_date = request.GET.get("currentDate")

        round_start_from = datetime.strptime(round_start_from, "%d-%m-%Y") if round_start_from else None
        round_start_to = datetime.strptime(round_start_to, "%d-%m-%Y") if round_start_to else None
        current_date = datetime(self.get_year(current_date), 1, 1) if current_date else datetime(self.get_year(), 1, 1)
        # get the filter query on start from and start to dates
        query_rounds = Q()
        if not round_start_from and not round_start_to:
            query_rounds = Q(started_at__gte=current_date)
        else:
            if round_start_from:
                query_rounds &= Q(started_at__gte=round_start_from)
            if round_start_to:
                query_rounds &= Q(started_at__lte=round_start_to)

        rounds = (
            Round.objects.select_related("campaign")
            .filter(query_rounds)
            .exclude(Q(campaign__isnull=True) | Q(campaign__is_test=True))
        )

        # get filtered rounds
        rounds = self.get_filtered_rounds(rounds, request.GET)
        # The csv file name base on the start from and start to dates
        start_from_name = (
            "--start-from-" + round_start_from.strftime("%d-%m-%Y")
            if round_start_from
            else ("--start-from-" + current_date.strftime("%d-%m-%Y") if not round_start_to else "")
        )
        start_to_name = "--start-to-" + round_start_to.strftime("%d-%m-%Y") if round_start_to else ""

        filename = "%s%s%s" % (
            "all-rounds-scopes",
            start_from_name,
            start_to_name,
        )
        # get csv columns
        columns = self.csv_columns()
        org_units_list = []
        # loop on filtered rounds and make the org_units_list to be pushed in the csv file
        for round in rounds:
            org_units_list += self.get_org_units_list(round, round.campaign)

        response = StreamingHttpResponse(
            streaming_content=(iter_items(org_units_list, Echo(), columns, self.get_row)), content_type=CONTENT_TYPE_CSV
        )
        filename = filename + ".csv"
        response["Content-Disposition"] = "attachment; filename=%s" % filename

        return response

    @action(methods=["GET"], detail=False, serializer_class=None)
    def csv_campaign_scopes_export(self, request, **kwargs):
        """
        It generates a csv export file with round's related informations

            parameters:
                self: a self
                round: an integer representing the round id
            returns:
                it generates a csv file export
        """
        round = Round.objects.get(pk=request.GET.get("round"))
        campaign = round.campaign
        org_units_list = self.get_org_units_list(round, campaign)

        filename = "%s-%s--%s--%s-%s" % (
            "campaign",
            campaign.obr_name,
            "R" + str(round.number),
            "org_units",
            strftime("%Y-%m-%d-%H-%M", gmtime()),
        )
        columns = self.csv_columns()

        response = StreamingHttpResponse(
            streaming_content=(iter_items(org_units_list, Echo(), columns, self.get_row)), content_type=CONTENT_TYPE_CSV
        )
        filename = filename + ".csv"
        response["Content-Disposition"] = "attachment; filename=%s" % filename

        return response

    @action(methods=["GET"], detail=False, serializer_class=None)
    def csv_campaigns_export(self, request, **kwargs):
        """
        It generates a csv export for all campaigns and their related rounds information

            parameters:
                self: a self
            returns:
                it generates a csv file export
        """
        columns = self.campaign_csv_columns()
        queryset = self.get_queryset()

        if not request.query_params.get("deletion_status"):
            queryset = queryset.filter(deleted_at__isnull=True)

        campaigns = self.filter_queryset(queryset)
        rounds = Round.objects.order_by("campaign__created_at").filter(campaign_id__in=campaigns)
        data = []

        for round in rounds:
            item = {}
            campaign = campaigns.get(pk=round.campaign_id)
            country = campaign.country.name if campaign.country else ""
            obr_name = campaign.obr_name
            vaccine_types = campaign.vaccines_extended
            onset_date = campaign.onset_at
            round_number = round.number
            item["country"] = country
            item["obr_name"] = obr_name
            item["vaccine_types"] = vaccine_types
            item["round_number"] = round_number
            item["onset_date"] = onset_date
            item["round_start_date"] = round.started_at
            item["round_end_date"] = round.ended_at
            item["ra_submission_date"] = campaign.risk_assessment_first_draft_submitted_at
            item["ra_approval_date"] = campaign.risk_assessment_rrt_oprtt_approval_at
            item["who_disbursed_to_co_at"] = campaign.who_disbursed_to_co_at
            item["who_disbursed_to_moh_at"] = campaign.who_disbursed_to_moh_at
            item["unicef_disbursed_to_co_at"] = campaign.unicef_disbursed_to_co_at
            item["unicef_disbursed_to_moh_at"] = campaign.unicef_disbursed_to_moh_at
            item["gpei_coordinator"] = campaign.gpei_coordinator
            item["round_target_population"] = (
                round.target_population if (round.target_population and (round.target_population > 0)) else ""
            )

            item["doses_requested"] = round.doses_requested
            if round.lqas_district_failing == 0 and round.lqas_district_passing == 0:
                item["lqas_district_passing"] = ""
                item["lqas_district_failing"] = ""
            else:
                item["lqas_district_passing"] = round.lqas_district_passing
                item["lqas_district_failing"] = round.lqas_district_failing
            item["budget_approved_date"] = campaign.approved_at_WFEDITABLE
            item["budget_submitted_date"] = campaign.submitted_to_rrt_at_WFEDITABLE
            item["preparedness_sync_status"] = (
                round.preparedness_sync_status if round.preparedness_spreadsheet_url else ""
            )

            item["pv_notified_at"] = campaign.cvdpv2_notified_at
            item["preparedness_spreadsheet_url"] = round.preparedness_spreadsheet_url
            item["cost"] = int(float(round.cost)) if (round.cost and (float(round.cost) > 0)) else ""
            data.append(item)

        filename = "%s-%s--%s" % (
            "campaigns",
            "rounds",
            strftime("%Y-%m-%d-%H-%M", gmtime()),
        )

        response = StreamingHttpResponse(
            streaming_content=(iter_items(data, Echo(), columns, self.get_campain_row)),
            content_type=CONTENT_TYPE_CSV,
        )
        filename = filename + ".csv"
        response["Content-Disposition"] = "attachment; filename=%s" % filename

        return response

    @staticmethod
    def get_year(current_date=None):
        if current_date is not None:
            current_date = datetime.strptime(current_date, "%Y-%m-%d")
            current_date = current_date.date()
            return current_date.year
        else:
            today = datetime.today()
            return today.year

    @staticmethod
    def csv_columns():
        """
        It returns the csv file columns for round scopes
        """
        return [
            {"title": "ID", "width": 10},
            {"title": "Admin 2", "width": 25},
            {"title": "Admin 1", "width": 25},
            {"title": "Admin 0", "width": 25},
            {"title": "OBR Name", "width": 25},
            {"title": "Round Number", "width": 35},
            {"title": "Start date", "width": 35},
            {"title": "Vaccine", "width": 35},
        ]

    @staticmethod
    def campaign_csv_columns():
        """
        It returns the csv file columns for campaigns
        """

        return [
            {"title": "country", "width": 10},
            {"title": "obr_name", "width": 25},
            {"title": "vaccine_types", "width": 25},
            {"title": "onset_date", "width": 25},
            {"title": "pv_notified_at", "width": 25},
            {"title": "round_number", "width": 35},
            {"title": "round_start_date", "width": 35},
            {"title": "round_end_date", "width": 35},
            {"title": "ra_submission_date", "width": 35},
            {"title": "ra_approval_date", "width": 35},
            {"title": "budget_submitted_date", "width": 35},
            {"title": "budget_approved_date", "width": 35},
            {"title": "who_disbursed_to_co_at", "width": 35},
            {"title": "who_disbursed_to_moh_at", "width": 35},
            {"title": "unicef_disbursed_to_co_at", "width": 35},
            {"title": "unicef_disbursed_to_moh_at", "width": 35},
            {"title": "gpei_coordinator", "width": 35},
            {"title": "round_target_population", "width": 35},
            {"title": "doses_requested", "width": 35},
            {"title": "cost", "width": 35},
            {"title": "lqas_district_passing", "width": 35},
            {"title": "lqas_district_failing", "width": 35},
            {"title": "preparedness_spreadsheet_url", "width": 35},
            {"title": "preparedness_sync_status", "width": 35},
        ]

    @staticmethod
    def get_row(org_unit, **kwargs):
        """
        It get data to be display on a csv row from the org units list
            parameters:
                org_unit: an org unit
                kwargs: arguments dictionary
            return:
                returns a row of a csv file
        """
        campaign_scope_values = [
            org_unit.get("id"),
            org_unit.get("org_unit_name"),
            org_unit.get("org_unit_parent_name"),
            org_unit.get("org_unit_parent_of_parent_name"),
            org_unit.get("obr_name"),
            org_unit.get("round_number"),
            org_unit.get("start_date"),
            org_unit.get("vaccine"),
        ]

        return campaign_scope_values

    @staticmethod
    def get_campain_row(data, **kwargs):
        colums = CampaignViewSet.campaign_csv_columns()
        campaigns_data = []
        for column in colums:
            campaigns_data.append(data.get(column["title"]))
        return campaigns_data

    @staticmethod
    def get_filtered_rounds(rounds, params, exclude_test_rounds=False):
        """
        It returns the filtered rounds based on params from url
            parameters:
                rounds: list of rounds
                params: params from url
                exclude_test_rounds: whether to exclude test rounds or not
            return:
                returns filtered list of rounds
        """
        countries = params.get("countries") if params.get("countries") is not None else None
        campaign_groups = params.get("campaignGroups") if params.get("campaignGroups") is not None else None
        campaign_category = params.get("campaignCategory") if params.get("campaignCategory") is not None else None
        search = params.get("search")
        org_unit_groups = params.get("orgUnitGroups") if params.get("orgUnitGroups") is not None else None

        # Filter out test rounds if requested
        if exclude_test_rounds:
            rounds = rounds.filter(is_test=False)

        # Test campaigns should not appear in the xlsx calendar
        rounds = rounds.filter(campaign__is_test=False)
        if countries:
            rounds = rounds.filter(campaign__country_id__in=countries.split(","))
        if campaign_groups:
            rounds = rounds.filter(campaign__group_id__in=campaign_groups.split(","))
        if campaign_category == "preventive":
            rounds = rounds.filter(campaign__is_preventive=True)
        if campaign_category == "regular":
            rounds = rounds.filter(campaign__is_preventive=False).filter(campaign__is_test=False)
        if search:
            rounds = rounds.filter(Q(campaign__obr_name__icontains=search) | Q(campaign__epid__icontains=search))
        if org_unit_groups:
            rounds = rounds.filter(campaign__country__groups__in=org_unit_groups.split(","))
        return rounds

    @staticmethod
    def get_org_units_list(round, campaign):
        """
        It returns org units list as a list of items
            parameters:
                round: a round
                campaign: a campaign
            return:
                returns org units list as a list of items
        """
        org_units_list = []
        if not campaign.separate_scopes_per_round:
            scopes = campaign.scopes.prefetch_related("group__org_units__org_unit_type").prefetch_related(
                "group__org_units__parent__parent"
            )
        else:
            scopes = round.scopes.prefetch_related("group__org_units__org_unit_type").prefetch_related(
                "group__org_units__parent__parent"
            )

        for scope in scopes.all():
            for org_unit in scope.group.org_units.all():
                item = {}
                item["id"] = org_unit.id
                item["org_unit_name"] = org_unit.name

                if org_unit.parent:
                    item["org_unit_parent_name"] = org_unit.parent.name
                else:
                    item["org_unit_parent_name"] = ""

                if org_unit.parent and org_unit.parent.parent:
                    item["org_unit_parent_of_parent_name"] = org_unit.parent.parent.name
                else:
                    item["org_unit_parent_of_parent_name"] = ""

                item["obr_name"] = campaign.obr_name
                item["round_number"] = "R" + str(round.number)
                item["start_date"] = round.started_at
                item["vaccine"] = scope.vaccine
                org_units_list.append(item)
        return org_units_list

    def get_calendar_data(self: "CampaignViewSet", year: int, params: Any) -> Any:
        """
        Returns filtered rounds from database
        """
        rounds = Round.objects.filter(started_at__year=year)
        rounds = self.get_filtered_rounds(rounds, params, exclude_test_rounds=True)

        return self.loop_on_rounds(self, rounds)

    @staticmethod
    def loop_on_rounds(self: "CampaignViewSet", rounds: Union[QuerySet, List[Round]]) -> list:
        """
        Returns formatted rounds

            parameters:
                self (CampaignViewSet): a self CampaignViewSet
                rounds(rounds queryset): rounds queryset
            returns:
                rounds (list): list of rounds
        """
        data_row: list = []
        for round in rounds:
            if round.campaign is not None:
                if round.campaign.country is not None:
                    campaign = round.campaign
                    country = campaign.country
                    if not any(d["country_id"] == country.id for d in data_row):
                        row = {"country_id": country.id, "country_name": country.name}
                        month = round.started_at.month
                        row["rounds"] = {}
                        row["rounds"][str(month)] = []
                        row["rounds"][str(month)].append(self.get_round(round, campaign, country))
                        data_row.append(row)
                    else:
                        row = [sub for sub in data_row if sub["country_id"] == country.id][0]
                        row_index = data_row.index(row)
                        if row is not None:
                            month = round.started_at.month
                            if str(month) in data_row[row_index]["rounds"]:
                                data_row[row_index]["rounds"][str(month)].append(
                                    self.get_round(round, campaign, country)
                                )
                            else:
                                data_row[row_index]["rounds"][str(month)] = []
                                data_row[row_index]["rounds"][str(month)].append(
                                    self.get_round(round, campaign, country)
                                )
        return data_row

    def get_round(self: "CampaignViewSet", round: Round, campaign: Campaign, country: OrgUnit) -> dict:
        started_at = datetime.strftime(round.started_at, "%Y-%m-%d") if round.started_at is not None else None
        ended_at = datetime.strftime(round.ended_at, "%Y-%m-%d") if round.ended_at is not None else None
        obr_name = campaign.obr_name if campaign.obr_name is not None else ""
        round_number = round.number if round.number is not None else ""
        # count all districts in the country
        country_districts_count = country.descendants().filter(org_unit_type__category="DISTRICT").count()
        # count disticts related to the round
        round_districts_count = len(campaign.get_districts_for_round_number(round_number)) if round_number else 0
        districts_exists = country_districts_count > 0 and round_districts_count > 0
        # check if country districts is equal to round districts
        if districts_exists:
            nid_or_snid = "NID" if country_districts_count == round_districts_count else "sNID"
        else:
            nid_or_snid = ""

        # percentage target population
        percentage_covered_target_population = (
            round.percentage_covered_target_population if round.percentage_covered_target_population is not None else ""
        )

        # target population
        target_population = round.target_population if round.target_population is not None else ""

        return {
            "started_at": started_at,
            "ended_at": ended_at,
            "obr_name": obr_name,
            "vaccines": round.vaccine_names,
            "round_number": round_number,
            "percentage_covered_target_population": percentage_covered_target_population,
            "target_population": target_population,
            "nid_or_snid": nid_or_snid,
        }

    @action(methods=["POST"], detail=True, serializer_class=CampaignPreparednessSpreadsheetSerializer)
    def create_preparedness_sheet(self, request: Request, pk=None, **kwargs):
        data = request.data
        data["campaign"] = pk
        serializer = CampaignPreparednessSpreadsheetSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    NEW_CAMPAIGN_MESSAGE = """Dear GPEI coordinator – {country_name}

This is an automated email.

Following the newly confirmed virus {virus_type} reported from {initial_orgunit_name} with date of onset/sample collection {onset_date}. \
A new outbreak {obr_name} has been created on the timeline tracker, to visualize the campaign visit: {url_campaign}

Some campaign details are missing at this stage. It is important to update the outbreak response information on this link {url}, \
to ensure optimal coordination of activities. The information should be updated at least weekly. Details for log in will be provided.

For more follow up: contact RRT team.

Timeline tracker Automated message
    """

    @action(methods=["POST"], detail=True, serializer_class=serializers.Serializer)
    def send_notification_email(self, request, pk, **kwargs):
        campaign = get_object_or_404(Campaign, pk=pk)
        old_campaign_dump = serialize_campaign(campaign)
        country = campaign.country

        domain = settings.DNS_DOMAIN
        from_email = settings.DEFAULT_FROM_EMAIL

        if campaign.creation_email_send_at:
            raise serializers.ValidationError("Notification Email already sent")
        if not (campaign.obr_name and campaign.virus and country and campaign.onset_at):
            raise serializers.ValidationError("Missing information on the campaign")

        email_text = self.NEW_CAMPAIGN_MESSAGE.format(
            country_name=country.name,
            obr_name=campaign.obr_name,
            virus_type=campaign.virus,
            onset_date=campaign.onset_at,
            initial_orgunit_name=campaign.initial_org_unit.name
            + (", " + campaign.initial_org_unit.parent.name if campaign.initial_org_unit.parent else ""),
            url=f"https://{domain}/dashboard/polio/list",
            url_campaign=f"https://{domain}/dashboard/polio/list/campaignId/{campaign.id}",
        )

        try:
            cug = CountryUsersGroup.objects.get(country=country)
        except CountryUsersGroup.DoesNotExist:
            raise serializers.ValidationError(
                f"Country {country.name} is not configured, please go to Configuration page"
            )
        users = cug.users.all()
        emails = [user.email for user in users if user.email]
        if not emails:
            raise serializers.ValidationError(f"No recipients have been configured on the country")

        send_mail(
            "New Campaign {}".format(campaign.obr_name),
            email_text,
            from_email,
            emails,
        )
        campaign.creation_email_send_at = now()
        campaign.save()
        request_user = self.request.user
        log_campaign_modification(campaign, old_campaign_dump, request_user)

        return Response({"message": "email sent"})

    # We need to authorize PATCH request to enable restore_deleted_campaign endpoint
    # But Patching the campign directly is very much error prone, so we disable it indirectly
    def partial_update(self):
        """Don't PATCH this way, it won't do anything
        We need to authorize PATCH request to enable restore_deleted_campaign endpoint
        But Patching the campign directly is very much error prone, so we disable it indirectly
        """
        pass

    @action(methods=["PATCH"], detail=False)
    def restore_deleted_campaigns(self, request):
        campaign = get_object_or_404(Campaign, pk=request.data["id"])
        if campaign.deleted_at is not None:
            campaign.deleted_at = None
            campaign.save()
            return Response(campaign.id, status=status.HTTP_200_OK)
        else:
            return Response("Campaign already active.", status=status.HTTP_400_BAD_REQUEST)

    @action(
        methods=["GET", "HEAD"],  # type: ignore # HEAD is missing in djangorestframework-stubs
        detail=False,
        url_path="v3/merged_shapes.geojson",
    )
    def shapes_v3(self, request):
        """
        Merged shapes for the campaign. Used for the calendar
        """
        campaigns = self.filter_queryset(self.get_queryset())
        # Remove deleted campaigns
        campaigns = campaigns.filter(deleted_at=None)
        campaigns = campaigns.only("geojson")
        features = []
        for c in campaigns:
            if c.geojson:
                features.extend(c.geojson)

        res = {"type": "FeatureCollection", "features": features}

        return JsonResponse(res)
