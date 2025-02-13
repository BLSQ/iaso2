import datetime
import enum
from django.db.models import OuterRef, Subquery, Exists, Q, Sum
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import filters, serializers, status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.utils.dateparse import parse_date
from hat.menupermissions import models as permission
from iaso.api.common import GenericReadWritePerm, ModelViewSet, Paginator
from iaso.models import OrgUnit
from plugins.polio.models import (
    DOSES_PER_VIAL,
    Campaign,
    DestructionReport,
    IncidentReport,
    OutgoingStockMovement,
    Round,
    VaccineArrivalReport,
    VaccineRequestForm,
    VaccineStock,
    EarmarkedStock,
)

vaccine_stock_id_param = openapi.Parameter(
    name="vaccine_stock",
    in_=openapi.IN_QUERY,
    description="The Vaccine Stock id related to the current object",
    type=openapi.TYPE_INTEGER,
    required=False,
)


class MovementTypeEnum(enum.Enum):
    DESTRUCTION_REPORT = "destruction_report"
    INCIDENT_REPORT = "incident_report"
    OUTGOING_STOCK_MOVEMENT = "outgoing_stock_movement"
    VACCINE_ARRIVAL_REPORT = "vaccine_arrival_report"


class VaccineStockCalculator:
    def __init__(self, vaccine_stock: VaccineStock):
        if not isinstance(vaccine_stock, VaccineStock):
            raise TypeError("vaccine_stock must be a VaccineStock object")

        self.vaccine_stock = vaccine_stock
        self.arrival_reports = VaccineArrivalReport.objects.filter(
            request_form__campaign__country=vaccine_stock.country, request_form__vaccine_type=vaccine_stock.vaccine
        )
        self.destruction_reports = DestructionReport.objects.filter(vaccine_stock=vaccine_stock).order_by(
            "destruction_report_date"
        )
        self.incident_reports = IncidentReport.objects.filter(vaccine_stock=vaccine_stock).order_by(
            "date_of_incident_report"
        )
        self.stock_movements = OutgoingStockMovement.objects.filter(vaccine_stock=vaccine_stock).order_by("report_date")
        self.earmarked_stocks = EarmarkedStock.objects.filter(vaccine_stock=vaccine_stock).order_by("created_at")

    def get_doses_per_vial(self):
        return DOSES_PER_VIAL[self.vaccine_stock.vaccine]

    def get_vials_used(self, end_date=None):
        results = self.get_list_of_used_vials(end_date)
        total = 0
        for result in results:
            total += result["vials_in"]

        return total

    def get_vials_destroyed(self, end_date=None):
        if not self.destruction_reports.exists():
            return 0
        destruction_reports = self.destruction_reports
        if end_date:
            destruction_reports = destruction_reports.filter(destruction_report_date__lte=end_date)
        return sum(report.unusable_vials_destroyed or 0 for report in destruction_reports)

    def get_total_of_usable_vials(self, end_date=None):
        results = self.get_list_of_usable_vials(end_date)
        total_vials_in = 0
        total_doses_in = 0

        for result in results:
            if result["vials_in"]:
                total_vials_in += result["vials_in"]
            if result["doses_in"]:
                total_doses_in += result["doses_in"]
            if result["vials_out"]:
                total_vials_in -= result["vials_out"]
            if result["doses_out"]:
                total_doses_in -= result["doses_out"]

        return total_vials_in, total_doses_in

    def get_vials_received(self, end_date=None):
        results = self.get_list_of_vaccines_received(end_date)

        total_vials_in = 0

        for result in results:
            if result["vials_in"]:
                total_vials_in += result["vials_in"]

        return total_vials_in

    def get_total_of_unusable_vials(self, end_date=None):
        results = self.get_list_of_unusable_vials(end_date)

        total_vials_in = 0
        total_doses_in = 0

        for result in results:
            if result["vials_in"]:
                total_vials_in += result["vials_in"]
            if result["doses_in"]:
                total_doses_in += result["doses_in"]
            if result["vials_out"]:
                total_vials_in -= result["vials_out"]
            if result["doses_out"]:
                total_doses_in -= result["doses_out"]

        return total_vials_in, total_doses_in

    def get_total_of_earmarked(self, end_date=None):
        earmarked_list = self.get_list_of_earmarked(end_date)

        total_vials = 0
        total_doses = 0

        for entry in earmarked_list:
            if entry["vials_in"]:
                total_vials += entry["vials_in"]
            if entry["doses_in"]:
                total_doses += entry["doses_in"]
            if entry["vials_out"]:
                total_vials -= entry["vials_out"]
            if entry["doses_out"]:
                total_doses -= entry["doses_out"]

        return total_vials, total_doses

    def get_list_of_vaccines_received(self, end_date=None):
        """
        Vaccines received are only those linked to an arrival report. We exclude those found e.g. during physical inventory
        """
        # First find the corresponding VaccineRequestForms
        vrfs = VaccineRequestForm.objects.filter(
            campaign__country=self.vaccine_stock.country, vaccine_type=self.vaccine_stock.vaccine
        )
        if end_date:
            eligible_rounds = (
                Round.objects.filter(campaign=OuterRef("campaign"))
                .filter(
                    (
                        Q(campaign__separate_scopes_per_round=False)
                        & Q(campaign__scopes__vaccine=self.vaccine_stock.vaccine)
                    )
                    | (Q(campaign__separate_scopes_per_round=True) & Q(scopes__vaccine=self.vaccine_stock.vaccine))
                )
                .filter(ended_at__lte=end_date)
                .filter(id__in=OuterRef("rounds"))
            )
            vrfs = vrfs.filter(Exists(Subquery(eligible_rounds)))

        if not vrfs.exists():
            arrival_reports = []
        else:
            # Then find the corresponding VaccineArrivalReports
            arrival_reports = VaccineArrivalReport.objects.filter(request_form__in=vrfs)
            if end_date:
                arrival_reports = arrival_reports.filter(arrival_report_date__lte=end_date)
            if not arrival_reports.exists():
                arrival_reports = []
        results = []

        for report in arrival_reports:
            results.append(
                {
                    "date": report.arrival_report_date,
                    "action": "PO #" + report.po_number if report.po_number else "Stock Arrival",
                    "vials_in": report.vials_received or 0,
                    "doses_in": report.doses_received or 0,
                    "vials_out": None,
                    "doses_out": None,
                    "type": MovementTypeEnum.VACCINE_ARRIVAL_REPORT.value,
                }
            )
        return results

    def get_list_of_usable_vials(self, end_date=None):
        # First get vaccines received from arrival reports
        results = self.get_list_of_vaccines_received(end_date)

        # Add stock movements (used and missing vials)
        stock_movements = OutgoingStockMovement.objects.filter(vaccine_stock=self.vaccine_stock).order_by("report_date")
        if end_date:
            stock_movements = stock_movements.filter(report_date__lte=end_date)
        for movement in stock_movements:
            if movement.earmarked_stocks.count() > 0:
                earmarked_stock_vials = movement.earmarked_stocks.aggregate(total=Sum("vials_earmarked"))["total"] or 0
                real_vials_used = movement.usable_vials_used - earmarked_stock_vials
                results.append(
                    {
                        "date": movement.report_date,
                        "action": f"Form A - Vials Used ({earmarked_stock_vials} vials from Earmarked, {real_vials_used} vials used from stock)",
                        "vials_in": None,
                        "doses_in": None,
                        "vials_out": real_vials_used or 0,
                        "doses_out": (real_vials_used or 0) * self.get_doses_per_vial(),
                        "type": MovementTypeEnum.OUTGOING_STOCK_MOVEMENT.value,
                    }
                )
            else:
                if movement.usable_vials_used > 0:
                    results.append(
                        {
                            "date": movement.report_date,
                            "action": "Form A - Vials Used",
                            "vials_in": None,
                            "doses_in": None,
                            "vials_out": movement.usable_vials_used or 0,
                            "doses_out": (movement.usable_vials_used or 0) * self.get_doses_per_vial(),
                            "type": MovementTypeEnum.OUTGOING_STOCK_MOVEMENT.value,
                        }
                    )

                if movement.missing_vials > 0:
                    results.append(
                        {
                            "date": movement.report_date,
                            "action": "Form A - Missing Vials",
                            "vials_in": None,
                            "doses_in": None,
                            "vials_out": movement.missing_vials or 0,
                            "doses_out": (movement.missing_vials or 0) * self.get_doses_per_vial(),
                            "type": MovementTypeEnum.OUTGOING_STOCK_MOVEMENT.value,
                        }
                    )

        # Add incident reports (IN movements then OUT movements)
        incident_reports = IncidentReport.objects.filter(vaccine_stock=self.vaccine_stock).order_by(
            "date_of_incident_report"
        )
        if end_date:
            incident_reports = incident_reports.filter(date_of_incident_report__lte=end_date)
        for report in incident_reports:
            if (
                report.usable_vials > 0
                and report.stock_correction == IncidentReport.StockCorrectionChoices.PHYSICAL_INVENTORY_ADD
            ):
                results.append(
                    {
                        "date": report.date_of_incident_report,
                        "action": report.stock_correction,
                        "vials_in": report.usable_vials or 0,
                        "doses_in": (report.usable_vials or 0) * self.get_doses_per_vial(),
                        "vials_out": None,
                        "doses_out": None,
                        "type": MovementTypeEnum.INCIDENT_REPORT.value,
                    }
                )
            if (
                report.usable_vials > 0
                and report.stock_correction == IncidentReport.StockCorrectionChoices.PHYSICAL_INVENTORY_REMOVE
            ):
                results.append(
                    {
                        "date": report.date_of_incident_report,
                        "action": report.stock_correction,
                        "vials_in": None,
                        "doses_in": None,
                        "vials_out": report.usable_vials or 0,
                        "doses_out": (report.usable_vials or 0) * self.get_doses_per_vial(),
                        "type": MovementTypeEnum.INCIDENT_REPORT.value,
                    }
                )
            if report.usable_vials > 0 and (
                report.stock_correction == IncidentReport.StockCorrectionChoices.LOSSES
                or report.stock_correction == IncidentReport.StockCorrectionChoices.RETURN
                or report.stock_correction == IncidentReport.StockCorrectionChoices.STEALING
                or report.stock_correction == IncidentReport.StockCorrectionChoices.BROKEN
            ):
                results.append(
                    {
                        "date": report.date_of_incident_report,
                        "action": report.stock_correction,
                        "vials_in": None,
                        "doses_in": None,
                        "vials_out": report.usable_vials or 0,
                        "doses_out": (report.usable_vials or 0) * self.get_doses_per_vial(),
                        "type": MovementTypeEnum.INCIDENT_REPORT.value,
                    }
                )
            if report.unusable_vials > 0 and (
                report.stock_correction == IncidentReport.StockCorrectionChoices.VACCINE_EXPIRED
                or report.stock_correction == IncidentReport.StockCorrectionChoices.VVM_REACHED_DISCARD_POINT
                or report.stock_correction == IncidentReport.StockCorrectionChoices.UNREADABLE_LABEL
            ):
                results.append(
                    {
                        "date": report.date_of_incident_report,
                        "action": report.stock_correction,
                        "vials_in": None,
                        "doses_in": None,
                        "vials_out": report.unusable_vials or 0,
                        "doses_out": (report.unusable_vials or 0) * self.get_doses_per_vial(),
                        "type": MovementTypeEnum.INCIDENT_REPORT.value,
                    }
                )

        earmarked_stocks = self.earmarked_stocks
        if end_date:
            earmarked_stocks = earmarked_stocks.filter(created_at__lte=end_date)

        for stock in earmarked_stocks:
            if stock.earmarked_stock_type == EarmarkedStock.EarmarkedStockChoices.CREATED:
                results.append(
                    {
                        "date": stock.created_at.date(),
                        "action": f"Earmarked created for {stock.campaign.obr_name} Round {stock.round.number}",
                        "vials_in": None,
                        "doses_in": None,
                        "vials_out": stock.vials_earmarked,
                        "doses_out": stock.doses_earmarked,
                        "type": "earmarked_stock__created",
                    }
                )
            elif stock.earmarked_stock_type == EarmarkedStock.EarmarkedStockChoices.RETURNED:
                results.append(
                    {
                        "date": stock.created_at.date(),
                        "action": f"Earmarked returned for {stock.campaign.obr_name} Round {stock.round.number}",
                        "vials_in": stock.vials_earmarked,
                        "doses_in": stock.doses_earmarked,
                        "vials_out": None,
                        "doses_out": None,
                        "type": "earmarked_stock__returned",
                    }
                )

        return results

    def get_list_of_used_vials(self, end_date=None):
        # Used vials are those related to formA outgoing movements. Vials with e.g expired date become unusable, but have not been used
        outgoing_movements = OutgoingStockMovement.objects.filter(vaccine_stock=self.vaccine_stock)
        if end_date:
            outgoing_movements = outgoing_movements.filter(report_date__lte=end_date)
        results = []
        for movement in outgoing_movements:
            if movement.usable_vials_used > 0:
                if movement.earmarked_stocks.count() > 0:
                    earmarked_stock_vials = (
                        movement.earmarked_stocks.aggregate(total=Sum("vials_earmarked"))["total"] or 0
                    )
                    desc_text = f"Form A - Vials Used ({earmarked_stock_vials} vials from Earmarked)"

                else:
                    desc_text = "Form A - Vials Used"

                results.append(
                    {
                        "date": movement.report_date,
                        "action": desc_text,
                        "vials_out": None,
                        "doses_out": None,
                        "vials_in": movement.usable_vials_used or 0,
                        "doses_in": (movement.usable_vials_used or 0) * self.get_doses_per_vial(),
                        "type": MovementTypeEnum.OUTGOING_STOCK_MOVEMENT.value,
                    }
                )
        return results

    def get_list_of_unusable_vials(self, end_date=None):
        # First get the used vials
        results = self.get_list_of_used_vials(end_date)

        # Get all IncidentReports and Destruction reports for the VaccineStock
        incident_reports = IncidentReport.objects.filter(vaccine_stock=self.vaccine_stock)
        if end_date:
            incident_reports = incident_reports.filter(date_of_incident_report__lte=end_date)

        destruction_reports = DestructionReport.objects.filter(vaccine_stock=self.vaccine_stock).order_by(
            "destruction_report_date"
        )
        if end_date:
            destruction_reports = destruction_reports.filter(destruction_report_date__lte=end_date)

        for report in destruction_reports:
            results.append(
                {
                    "date": report.destruction_report_date,
                    "action": (f"{report.action}" if len(report.action) > 0 else f"Destruction report"),
                    "vials_in": None,
                    "doses_in": None,
                    "vials_out": report.unusable_vials_destroyed or 0,
                    "doses_out": (report.unusable_vials_destroyed or 0) * self.get_doses_per_vial(),
                    "type": MovementTypeEnum.DESTRUCTION_REPORT.value,
                }
            )

        # Add unusable vials from IncidentReports
        for report in incident_reports:
            if report.unusable_vials > 0 and (
                report.stock_correction == IncidentReport.StockCorrectionChoices.PHYSICAL_INVENTORY_ADD
                or report.stock_correction == IncidentReport.StockCorrectionChoices.VACCINE_EXPIRED
                or report.stock_correction == IncidentReport.StockCorrectionChoices.VVM_REACHED_DISCARD_POINT
                or report.stock_correction == IncidentReport.StockCorrectionChoices.UNREADABLE_LABEL
                or report.stock_correction == IncidentReport.StockCorrectionChoices.BROKEN
            ):
                results.append(
                    {
                        "date": report.date_of_incident_report,
                        "action": report.stock_correction,  # for every field FOO that has choices set, the object will have a get_FOO_display() method
                        "vials_in": report.unusable_vials or 0,
                        "doses_in": (report.unusable_vials or 0) * self.get_doses_per_vial(),
                        "vials_out": None,
                        "doses_out": None,
                        "type": MovementTypeEnum.INCIDENT_REPORT.value,
                    }
                )
            if report.unusable_vials > 0 and (
                report.stock_correction == IncidentReport.StockCorrectionChoices.PHYSICAL_INVENTORY_REMOVE
            ):
                results.append(
                    {
                        "date": report.date_of_incident_report,
                        "action": report.stock_correction,  # for every field FOO that has choices set, the object will have a get_FOO_display() method
                        "vials_in": None,
                        "doses_in": None,
                        "vials_out": report.unusable_vials or 0,
                        "doses_out": (report.unusable_vials or 0) * self.get_doses_per_vial(),
                        "type": MovementTypeEnum.INCIDENT_REPORT.value,
                    }
                )

        # Add earmarked stock movements of type USED
        earmarked_stocks = self.earmarked_stocks.filter(
            vaccine_stock=self.vaccine_stock, earmarked_stock_type=EarmarkedStock.EarmarkedStockChoices.USED
        )

        if end_date:
            earmarked_stocks = earmarked_stocks.filter(created_at__date__lte=end_date)

        for stock in earmarked_stocks:
            if (
                stock.earmarked_stock_type == EarmarkedStock.EarmarkedStockChoices.USED and stock.form_a is None
            ):  # if FormA is not None, it's accounted by the FormA, no need to repeat
                results.append(
                    {
                        "date": stock.created_at.date(),
                        "action": f"Earmarked stock used for {stock.campaign.obr_name} Round {stock.round.number}",
                        "vials_in": stock.vials_earmarked,
                        "doses_in": stock.doses_earmarked,
                        "vials_out": None,
                        "doses_out": None,
                        "type": "earmarked_stock__used",
                    }
                )

        return results

    def get_list_of_earmarked(self, end_date=None):
        earmarked_movements = self.earmarked_stocks
        if end_date:
            earmarked_movements = earmarked_movements.filter(created_at__lte=end_date)

        results = []
        for movement in earmarked_movements:
            movement_type = movement.earmarked_stock_type
            if (
                movement_type == EarmarkedStock.EarmarkedStockChoices.USED
                or movement_type == EarmarkedStock.EarmarkedStockChoices.RETURNED
            ):
                if movement.form_a is not None:
                    action_text = f"Earmarked stock used for FormA ({movement.form_a})"
                else:
                    action_text = f"Earmarked stock used for {movement.campaign.obr_name} Round {movement.round.number}"

                results.append(
                    {
                        "date": movement.created_at,
                        "action": action_text,
                        "vials_out": movement.vials_earmarked,
                        "doses_out": movement.doses_earmarked,
                        "vials_in": None,
                        "doses_in": None,
                        "type": f"earmarked_stock__{movement_type}",
                    }
                )
            else:
                results.append(
                    {
                        "date": movement.created_at,
                        "action": f"Earmarked stock reserved for {movement.campaign.obr_name} Round {movement.round.number}",
                        "vials_in": movement.vials_earmarked,
                        "doses_in": movement.doses_earmarked,
                        "vials_out": None,
                        "doses_out": None,
                        "type": f"earmarked_stock__{movement_type}",
                    }
                )
        return results


class VaccineStockListSerializer(serializers.ListSerializer):
    @staticmethod
    def calculate_for_instance(instance):
        instance.calculator = VaccineStockCalculator(instance)

    def to_representation(self, data):
        """
        List of object instances -> List of dicts of primitive datatypes.
        """
        # Calculate once for each instance
        for instance in data:
            self.calculate_for_instance(instance)
        return [VaccineStockSerializer(instance).data for instance in data]


class VaccineStockSerializer(serializers.ModelSerializer):
    country_name = serializers.CharField(source="country.name")
    country_id = serializers.IntegerField(source="country.id")
    vaccine_type = serializers.CharField(source="vaccine")
    vials_received = serializers.SerializerMethodField()
    vials_used = serializers.SerializerMethodField()
    stock_of_usable_vials = serializers.SerializerMethodField()
    stock_of_unusable_vials = serializers.SerializerMethodField()
    vials_destroyed = serializers.SerializerMethodField()

    class Meta:
        model = VaccineStock
        fields = [
            "id",
            "country_name",
            "country_id",
            "vaccine_type",
            "vials_received",
            "vials_used",
            "stock_of_usable_vials",
            "stock_of_unusable_vials",
            "vials_destroyed",
        ]
        list_serializer_class = VaccineStockListSerializer

    def get_vials_received(self, obj):
        return obj.calculator.get_vials_received()

    def get_vials_used(self, obj):
        return obj.calculator.get_vials_used()

    def get_stock_of_usable_vials(self, obj):
        return obj.calculator.get_total_of_usable_vials()[0]

    def get_stock_of_unusable_vials(self, obj):
        return obj.calculator.get_total_of_unusable_vials()[0]

    def get_vials_destroyed(self, obj):
        return obj.calculator.get_vials_destroyed()


class VaccineStockCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = VaccineStock
        fields = ["country", "vaccine"]

    def create(self, validated_data):
        validated_data["account"] = self.context["request"].user.iaso_profile.account

        return VaccineStock.objects.create(**validated_data)


class VaccineStockManagementReadWritePerm(GenericReadWritePerm):
    read_perm = permission.POLIO_VACCINE_STOCK_MANAGEMENT_READ
    write_perm = permission.POLIO_VACCINE_STOCK_MANAGEMENT_WRITE


class StockManagementCustomFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, _view):
        country_id = request.GET.get("country_id")
        vaccine_type = request.GET.get("vaccine_type")
        country_blocks = request.GET.get("country_blocks", None)

        if country_id:
            queryset = queryset.filter(country_id__in=country_id.split(","))
        if vaccine_type:
            queryset = queryset.filter(vaccine=vaccine_type)
        if country_blocks:
            try:
                queryset = queryset.filter(country__groups__in=country_blocks.split(","))
            except:
                pass

        current_order = request.GET.get("order")

        if current_order:
            if current_order == "country_name":
                queryset = queryset.order_by("country__name")
            elif current_order == "-country_name":
                queryset = queryset.order_by("-country__name")
            elif current_order == "vaccine_type":
                queryset = queryset.order_by("vaccine")
            elif current_order == "-vaccine_type":
                queryset = queryset.order_by("-vaccine")

        return queryset


class VaccineStockSubitemBase(ModelViewSet):
    allowed_methods = ["get", "post", "head", "options", "patch", "delete"]
    permission_classes = [VaccineStockManagementReadWritePerm]
    model_class = None

    @swagger_auto_schema(
        manual_parameters=[vaccine_stock_id_param],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        vaccine_stock_id = self.request.query_params.get("vaccine_stock")
        order = self.request.query_params.get("order")

        if self.model_class is None:
            raise NotImplementedError("model_class must be defined")

        queryset = self.model_class.objects.filter(vaccine_stock__account=self.request.user.iaso_profile.account)

        if vaccine_stock_id is not None:
            queryset = queryset.filter(vaccine_stock=vaccine_stock_id)

        if order:
            queryset = queryset.order_by(order)

        return queryset


class VaccineStockSubitemEdit(VaccineStockSubitemBase):
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Extract campaign data
        campaign_obr_name = serializer.validated_data.get("campaign").get("obr_name")
        round_number = serializer.validated_data.get("round").get("number")

        # Get campaign and round objects
        campaign = Campaign.objects.get(obr_name=campaign_obr_name, account=request.user.iaso_profile.account)
        _round = campaign.rounds.get(number=round_number)

        # Update validated data
        serializer.validated_data["campaign"] = campaign
        serializer.validated_data["round"] = _round

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # Extract campaign data
        campaign_obr_name = serializer.validated_data.get("campaign").get("obr_name")
        round_number = serializer.validated_data.get("round").get("number")

        # Get campaign and round objects
        campaign = Campaign.objects.get(obr_name=campaign_obr_name, account=request.user.iaso_profile.account)
        _round = campaign.rounds.get(number=round_number)

        serializer.validated_data["campaign"] = campaign
        serializer.validated_data["round"] = _round

        self.perform_update(serializer)
        return Response(serializer.data)


class OutgoingStockMovementSerializer(serializers.ModelSerializer):
    campaign = serializers.CharField(source="campaign.obr_name")
    document = serializers.FileField(required=False)
    round_number = serializers.SerializerMethodField()

    class Meta:
        model = OutgoingStockMovement
        fields = [
            "id",
            "campaign",
            "vaccine_stock",
            "report_date",
            "form_a_reception_date",
            "usable_vials_used",
            "lot_numbers",
            "missing_vials",
            "document",
            "comment",
            "round",
            "round_number",
        ]

    def get_round_number(self, obj):
        return obj.round.number if obj.round else None

    def extract_campaign_data(self, validated_data):
        campaign_data = validated_data.pop("campaign", None)
        if campaign_data:
            campaign_obr_name = campaign_data.get("obr_name")
            campaign = Campaign.objects.get(
                obr_name=campaign_obr_name, account=self.context["request"].user.iaso_profile.account
            )
            return campaign
        return None

    def create(self, validated_data):
        campaign = self.extract_campaign_data(validated_data)
        if campaign:
            validated_data["campaign"] = campaign
        return OutgoingStockMovement.objects.create(**validated_data)

    def update(self, instance, validated_data):
        campaign = self.extract_campaign_data(validated_data)
        if campaign:
            instance.campaign = campaign
        return super().update(instance, validated_data)


class OutgoingStockMovementViewSet(VaccineStockSubitemBase):
    serializer_class = OutgoingStockMovementSerializer
    model_class = OutgoingStockMovement

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)

        # When Form A is created, find if there is a matching earmarked stock
        # and create a new earmarked stock of type USED with the same values
        if response.status_code == 201:
            movement = OutgoingStockMovement.objects.get(id=response.data["id"])
            if movement and movement.round and movement.vaccine_stock:
                total_vials_usable = EarmarkedStock.get_available_vials_count(movement.vaccine_stock, movement.round)

                vials_earmarked_used = min(total_vials_usable, movement.usable_vials_used)
                doses_earmarked_used = vials_earmarked_used * DOSES_PER_VIAL[movement.vaccine_stock.vaccine]

                if vials_earmarked_used > 0:
                    EarmarkedStock.objects.create(
                        vaccine_stock=movement.vaccine_stock,
                        campaign=movement.campaign,
                        round=movement.round,
                        earmarked_stock_type=EarmarkedStock.EarmarkedStockChoices.USED,
                        vials_earmarked=vials_earmarked_used,
                        doses_earmarked=doses_earmarked_used,
                        comment="Created from Form A submission",
                        form_a=movement,
                    )

        return response


class IncidentReportSerializer(serializers.ModelSerializer):
    document = serializers.FileField(required=False)

    class Meta:
        model = IncidentReport
        fields = "__all__"


class IncidentReportViewSet(VaccineStockSubitemBase):
    serializer_class = IncidentReportSerializer
    model_class = IncidentReport


class DestructionReportSerializer(serializers.ModelSerializer):
    document = serializers.FileField(required=False)

    class Meta:
        model = DestructionReport
        fields = "__all__"


class DestructionReportViewSet(VaccineStockSubitemBase):
    serializer_class = DestructionReportSerializer
    model_class = DestructionReport


class EarmarkedStockSerializer(serializers.ModelSerializer):
    campaign = serializers.CharField(source="campaign.obr_name")
    round_number = serializers.IntegerField(source="round.number")

    class Meta:
        model = EarmarkedStock
        fields = [
            "id",
            "vaccine_stock",
            "campaign",
            "round_number",
            "form_a",
            "earmarked_stock_type",
            "vials_earmarked",
            "doses_earmarked",
            "comment",
            "created_at",
            "updated_at",
        ]

    def extract_campaign_data(self, validated_data):
        campaign_data = validated_data.pop("campaign", None)
        if campaign_data:
            campaign_obr_name = campaign_data.get("obr_name")
            campaign = Campaign.objects.get(
                obr_name=campaign_obr_name, account=self.context["request"].user.iaso_profile.account
            )
            return campaign
        return None


class EarmarkedStockViewSet(VaccineStockSubitemEdit):
    serializer_class = EarmarkedStockSerializer
    model_class = EarmarkedStock

    def get_queryset(self):
        return EarmarkedStock.objects.filter(
            vaccine_stock__account=self.request.user.iaso_profile.account
        ).select_related("vaccine_stock", "campaign", "round")


class VaccineStockManagementViewSet(ModelViewSet):
    """
    ViewSet for managing Vaccine Stock data.

    This ViewSet provides actions to retrieve and manage stock information
    for vaccines, including summaries of usable and unusable vials, and
    detailed movements such as arrivals, destructions, and incidents.

    Available endpoints :

    GET /api/polio/vaccine/vaccine_stock/
    Return a list of summary informations for a VaccineStock. (Used by the Vaccine Stock list view)

    POST /api/polio/vaccine/vaccine_stock/
    Add a new VaccineStock.

    GET /api/polio/vaccine/vaccine_stock/{id}/
    Return a specific item from the previous list.

    DELETE /api/polio/vaccine/vaccine_stock/{id}/
    Delete a vaccine stock. All related OutgoingMovements, IncidentReports and Destructions will also be deleted.

    GET /api/polio/vaccine/vaccine_stock/{id}/summary/
    Return a summary of vaccine stock for a given VaccineStock ID (Used on detail page)

    GET /api/polio/vaccine/vaccine_stock/{id}/usable_vials/
    Return a detailed list of movements for usable vials associated with a given VaccineStock ID.

    GET /api/polio/vaccine/vaccine_stock/{id}/unusable_vials/
    Return a detailed list of movements for unusable vials associated with a given VaccineStock ID.



    """

    permission_classes = [VaccineStockManagementReadWritePerm]
    serializer_class = VaccineStockSerializer
    http_method_names = ["get", "head", "options", "post", "delete"]

    model = VaccineStock

    filter_backends = [SearchFilter, StockManagementCustomFilter]
    search_fields = ["vaccine", "country__name"]

    # We need to override this method to add the calculator on the instance
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if isinstance(instance, VaccineStock):
            instance.calculator = VaccineStockCalculator(instance)
        else:
            return Response({"error": "VaccineStock not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def create(self, request):
        """
        Add a new VaccineStock.

        This endpoint is used to add a new VaccineStock to the database.
        The request body should include the country ID and vaccine type.
        """
        serializer = VaccineStockCreateSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["get"])
    def summary(self, request, pk=None):
        """
        Retrieve a summary of vaccine stock for a given VaccineStock ID.

        The summary includes the country name, vaccine type, total usable and unusable vials,
        and corresponding doses.
        """
        if pk is None:
            return Response({"error": "No VaccineStock ID provided"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            vaccine_stock = self.get_queryset().get(id=pk)
        except VaccineStock.DoesNotExist:
            return Response({"error": "VaccineStock not found for "}, status=status.HTTP_404_NOT_FOUND)

        calculator = VaccineStockCalculator(vaccine_stock)

        total_usable_vials, total_usable_doses = calculator.get_total_of_usable_vials()
        total_unusable_vials, total_unusable_doses = calculator.get_total_of_unusable_vials()
        total_earmarked_vials, total_earmarked_doses = calculator.get_total_of_earmarked()

        summary_data = {
            "country_id": vaccine_stock.country.id,
            "country_name": vaccine_stock.country.name,
            "vaccine_type": vaccine_stock.vaccine,
            "total_usable_vials": total_usable_vials,
            "total_unusable_vials": total_unusable_vials,
            "total_usable_doses": total_usable_doses,
            "total_earmarked_vials": total_earmarked_vials,
            "total_earmarked_doses": total_earmarked_doses,
            "total_unusable_doses": total_unusable_doses,
        }

        return Response(summary_data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"])
    def usable_vials(self, request, pk=None):
        """
        Retrieve a detailed list of movements for usable vials associated with a given VaccineStock ID.

        This includes information on stock arrivals, destructions, incidents, and outgoing stock movements.
        Each movement is timestamped and includes the number of vials and doses affected.
        """
        if pk is None:
            return Response({"error": "No VaccineStock ID provided"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            vaccine_stock = self.get_queryset().get(id=pk)
        except VaccineStock.DoesNotExist:
            return Response({"error": "VaccineStock not found"}, status=status.HTTP_404_NOT_FOUND)

        end_date = request.query_params.get("end_date", None)
        if end_date:
            parsed_end_date = parse_date(end_date)
            if not parsed_end_date:
                raise ValidationError("The 'end_date' query parameter is not a valid date.")

        calc = VaccineStockCalculator(vaccine_stock)
        results = calc.get_list_of_usable_vials(end_date)
        results = self._sort_results(request, results)

        paginator = Paginator()
        page = paginator.paginate_queryset(results, request)
        if page is not None:
            return paginator.get_paginated_response(page)
        return Response({"results": results})

    @action(detail=True, methods=["get"])
    def get_unusable_vials(self, request, pk=None):
        """
        Retrieve a detailed list of movements for unusable vials associated with a given VaccineStock ID.

        This includes information on outgoing stock movements and incident reports
        that resulted in unusable vials, with each movement timestamped and including
        the number of vials and doses affected.
        """
        if pk is None:
            return Response({"error": "No VaccineStock ID provided"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            vaccine_stock = self.get_queryset().get(id=pk)
        except VaccineStock.DoesNotExist:
            return Response({"error": "VaccineStock not found"}, status=status.HTTP_404_NOT_FOUND)

        end_date = request.query_params.get("end_date", None)
        if end_date:
            parsed_end_date = parse_date(end_date)
            if not parsed_end_date:
                raise ValidationError("The 'end_date' query parameter is not a valid date.")

        calc = VaccineStockCalculator(vaccine_stock)
        results = calc.get_list_of_unusable_vials(end_date)
        results = self._sort_results(request, results)

        paginator = Paginator()
        page = paginator.paginate_queryset(results, request)
        if page is not None:
            return paginator.get_paginated_response(page)
        return Response({"results": results})

    @action(detail=True, methods=["get"])
    def get_earmarked_stock(self, request, pk=None):
        """
        Retrieve a detailed list of movements for earmarked stock associated with a given VaccineStock ID.

        """
        if pk is None:
            raise ValidationError("No VaccineStock ID provided")

        try:
            vaccine_stock = self.get_queryset().get(id=pk)
        except VaccineStock.DoesNotExist:
            raise ValidationError(f"VaccineStock not found for id={pk}")

        end_date = request.query_params.get("end_date", None)
        if end_date:
            parsed_end_date = parse_date(end_date)
            if not parsed_end_date:
                raise ValidationError("The 'end_date' query parameter is not a valid date.")

        calc = VaccineStockCalculator(vaccine_stock)
        results = calc.get_list_of_earmarked(end_date)
        results = self._sort_results(request, results)

        paginator = Paginator()
        page = paginator.paginate_queryset(results, request)
        if page is not None:
            return paginator.get_paginated_response(page)
        return Response({"results": results})

    def get_serializer_class(self):
        if self.action == "create":
            return VaccineStockCreateSerializer
        else:
            return VaccineStockSerializer

    def get_queryset(self):
        """
        Get the queryset for VaccineStock objects.

        The queryset is filtered by the account of the logged-in user and includes
        related destruction reports, incident reports, and outgoing stock movements.
        It is ordered by the VaccineStock ID.
        """

        accessible_org_units = OrgUnit.objects.filter_for_user_and_app_id(
            self.request.user, self.request.query_params.get("app_id")
        )
        accessible_org_units_ids = accessible_org_units.values_list("id", flat=True)

        return (
            VaccineStock.objects.filter(
                account=self.request.user.iaso_profile.account, country__id__in=accessible_org_units_ids
            )
            .prefetch_related("destructionreport_set", "incidentreport_set", "outgoingstockmovement_set")
            .distinct()
            .order_by("id")
        )

    def _sort_results(self, request: Request, results: list[dict]) -> list[dict]:
        order = request.query_params.get(OrderingFilter.ordering_param)
        reverse = False

        if order and order.startswith("-"):
            reverse = True
            order = order.removeprefix("-")

        valid_order_keys_and_defaults = {
            "date": datetime.datetime.min,
            "action": "",
            "vials_in": 0,
            "vials_out": 0,
            "doses_in": 0,
            "doses_out": 0,
        }

        if order not in valid_order_keys_and_defaults.keys():
            return sorted(results, key=lambda d: d["date"])

        return sorted(results, key=lambda d: d[order] or valid_order_keys_and_defaults[order], reverse=reverse)
