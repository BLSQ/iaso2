from django.db.models import OuterRef, Subquery
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import serializers

from iaso.api.common import EtlModelViewset, ModelViewSet
from plugins.polio.api.vaccines.stock_management import VaccineStockCalculator
from plugins.polio.api.vaccines.supply_chain import VaccineSupplyChainReadWritePerm
from plugins.polio.models import (
    DestructionReport,
    OutgoingStockMovement,
    VaccineArrivalReport,
    VaccinePreAlert,
    VaccineRequestForm,
    VaccineStock,
)
from plugins.polio.models.base import Campaign, Round


class VaccineRequestFormDashboardSerializer(serializers.ModelSerializer):
    obr_name = serializers.CharField(source="campaign.obr_name")
    country = serializers.IntegerField(source="campaign.country.pk")
    stock_in_hand = serializers.IntegerField(read_only=True)
    form_a_reception_date = serializers.DateField(read_only=True)
    destruction_report_reception_date = serializers.DateField(read_only=True)

    class Meta:
        model = VaccineRequestForm
        fields = "__all__"

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        accnt = self.context["request"].user.iaso_profile.account

        vaccine_stock, _ = VaccineStock.objects.get_or_create(
            country=instance.campaign.country, vaccine=instance.vaccine_type, account=accnt
        )

        representation["stock_in_hand"] = self.get_stock_in_hand(instance, vaccine_stock)
        representation["form_a_reception_date"] = self.get_form_a_reception_date(instance, vaccine_stock)
        representation["destruction_report_reception_date"] = self.get_destruction_report_reception_date(
            instance, vaccine_stock
        )

        return representation

    def get_stock_in_hand(self, obj, vaccine_stock):
        # Create a cache dictionary in the context if it doesn't exist
        if "stock_in_hand_cache" not in self.context:
            self.context["stock_in_hand_cache"] = {}

        # Create a unique key for this country and vaccine type
        cache_key = f"{obj.campaign.country.pk}_{obj.vaccine_type}"

        # If the value is not in the cache, calculate it
        if cache_key not in self.context["stock_in_hand_cache"]:
            vaccine_stock_calculator = VaccineStockCalculator(vaccine_stock)
            self.context["stock_in_hand_cache"][cache_key] = vaccine_stock_calculator.get_total_of_usable_vials()

        return self.context["stock_in_hand_cache"][cache_key]

    def get_form_a_reception_date(self, obj, vaccine_stock):
        # TODO: Remove this once the dashboard is updated to use the new form A model
        # It will get this info by joining on the FormA.round id
        latest_outgoing_stock_movement = (
            OutgoingStockMovement.objects.filter(vaccine_stock=vaccine_stock, campaign=obj.campaign)
            .order_by("-form_a_reception_date")
            .first()
        )
        return latest_outgoing_stock_movement.form_a_reception_date if latest_outgoing_stock_movement else None

    def get_destruction_report_reception_date(self, obj, vaccine_stock):
        first_round_start_date = (
            Round.objects.filter(campaign=obj.campaign)
            .order_by("started_at")
            .values_list("started_at", flat=True)
            .first()
        )

        earliest_round_start_date = (
            Round.objects.filter(campaign=OuterRef("pk")).order_by("started_at").values("started_at")[:1]
        )

        distinct_campaign_ids = (
            Campaign.objects.filter(
                country=vaccine_stock.country,
                rounds__started_at__gt=first_round_start_date,
                account=self.context["request"].user.iaso_profile.account,
            )
            .exclude(id=obj.campaign.id)  # We dont want to considerate the current campaign
            .order_by("id")
            .distinct("id")
            .values_list("id", flat=True)
        )

        campaigns_after_last_round = (
            Campaign.objects.filter(id__in=Subquery(distinct_campaign_ids))
            .annotate(earliest_round_start=Subquery(earliest_round_start_date))
            .order_by("earliest_round_start")
        )

        next_campaign_start_date = None

        for campaign in campaigns_after_last_round:
            if vaccine_stock.vaccine in campaign.single_vaccines_extended_list:
                # Do something if the vaccine matches
                next_campaign_start_date = (
                    Round.objects.filter(campaign=campaign)
                    .order_by("started_at")
                    .values_list("started_at", flat=True)
                    .first()
                )

        if first_round_start_date is not None and next_campaign_start_date is not None:
            sel_qs = DestructionReport.objects.filter(
                vaccine_stock=vaccine_stock,
                rrt_destruction_report_reception_date__gte=first_round_start_date,
                rrt_destruction_report_reception_date__lt=next_campaign_start_date,
            )
        elif first_round_start_date is not None:
            sel_qs = DestructionReport.objects.filter(
                vaccine_stock=vaccine_stock, rrt_destruction_report_reception_date__gt=first_round_start_date
            )
        else:
            sel_qs = DestructionReport.objects.filter(vaccine_stock=vaccine_stock)

        latest_destruction_report = sel_qs.order_by("-rrt_destruction_report_reception_date").first()

        return latest_destruction_report.rrt_destruction_report_reception_date if latest_destruction_report else None


class VaccineRequestFormDashboardViewSet(EtlModelViewset):
    """
    GET /api/polio/dashboards/vaccine_request_forms/
    Returns all vaccine request forms for the user's account.
    Simple endpoint that returns all model fields to facilitate data manipulation by OpenHexa or PowerBI
    3 additional fields have been added:
    - obr_name: the campaign's OBR name, that may need to be displayed
    - country: the id of the vaccine request form's country
    - stock_in_hand: the stock in hand calculated from VaccineStockCalculator
    - get_form_a_reception_date: Form A reception (RRT) date
    - get_destruction_report_reception_date: Destruction Report Received by RRT date
    """

    http_method_names = ["get"]
    permission_classes = [VaccineSupplyChainReadWritePerm]
    model = VaccineRequestForm
    serializer_class = VaccineRequestFormDashboardSerializer

    @method_decorator(cache_page(60 * 60))  # Cache for 1 hour
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        return VaccineRequestForm.objects.filter(
            campaign__account=self.request.user.iaso_profile.account
        ).select_related("campaign__country")


class VaccinePreAlertDashboardSerializer(serializers.ModelSerializer):
    class Meta:
        model = VaccinePreAlert
        fields = "__all__"


class PreAlertDashboardViewSet(EtlModelViewset):
    """
    GET /api/polio/dashboards/pre_alerts/
    Returns all vaccine pre alerts for the user's account.
    Simple endpoint that returns all model fields to facilitate data manipulation by OpenHexa or PowerBI
    """

    http_method_names = ["get"]
    permission_classes = [VaccineSupplyChainReadWritePerm]
    model = VaccinePreAlert
    serializer_class = VaccinePreAlertDashboardSerializer

    def get_queryset(self):
        return VaccinePreAlert.objects.filter(request_form__campaign__account=self.request.user.iaso_profile.account)


class VaccineArrivalReportDashboardSerializer(serializers.ModelSerializer):
    class Meta:
        model = VaccineArrivalReport
        fields = "__all__"


class VaccineArrivalReportDashboardViewSet(EtlModelViewset):
    """
    GET /api/polio/dashboards/arrival_reports/
    Returns all vaccine arrival reports for the user's account.
    Simple endpoint that returns all model fields to facilitate data manipulation by OpenHexa or PowerBI
    """

    http_method_names = ["get"]
    permission_classes = [VaccineSupplyChainReadWritePerm]
    model = VaccinePreAlert
    serializer_class = VaccineArrivalReportDashboardSerializer

    def get_queryset(self):
        return VaccineArrivalReport.objects.filter(
            request_form__campaign__account=self.request.user.iaso_profile.account
        )
