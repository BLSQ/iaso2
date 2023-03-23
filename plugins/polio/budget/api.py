from typing import Type
import csv
from rest_framework_csv import renderers as r
from datetime import datetime
from django.db.models import QuerySet, Max, Q
from django.http import HttpResponse
from django.shortcuts import redirect
from django_filters.rest_framework import DjangoFilterBackend  # type: ignore
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, filters, status, serializers
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from iaso.api.common import ModelViewSet, DeletionFilterBackend, HasPermission
from plugins.polio.budget.models import BudgetStep, MailTemplate, get_workflow, BudgetStepFile
from plugins.polio.budget.serializers import (
    CampaignBudgetSerializer,
    ExportCampaignBudgetSerializer,
    TransitionToSerializer,
    BudgetStepSerializer,
    UpdateBudgetStepSerializer,
    WorkflowSerializer,
    TransitionOverrideSerializer,
)
from plugins.polio.helpers import CustomFilterBackend
from plugins.polio.models import Campaign


# FIXME maybe: Maybe we should inherit from CampaignViewSet directly to not duplicate all the order and filter logic
# But then we would inherit all the other actions too
@swagger_auto_schema(tags=["budget"])
class BudgetCampaignViewSet(ModelViewSet):
    """
    Campaign endpoint with budget information.

    You can request specific field by using the ?fields parameter
    """

    serializer_class = CampaignBudgetSerializer
    permission_classes = [HasPermission("menupermissions.iaso_polio_budget")]  # type: ignore
    remove_results_key_if_paginated = True

    # Make this read only
    # FIXME : remove POST
    http_method_names = ["get", "head", "post"]
    filter_backends = [
        filters.OrderingFilter,
        DjangoFilterBackend,
        DeletionFilterBackend,
        CustomFilterBackend,
    ]

    def get_serializer_class(self):
        if "text/csv" in self.request.accepted_media_type:
            return ExportCampaignBudgetSerializer
        return super().get_serializer_class()

    def get_renderer_context(self):
        context = super().get_renderer_context()
        serializer_class = self.get_serializer_class()
        context["header"] = serializer_class.Meta.fields
        if hasattr(serializer_class.Meta, "labels"):
            context["labels"] = serializer_class.Meta.labels
        return context

    def get_queryset(self) -> QuerySet:
        user = self.request.user
        campaigns = Campaign.objects.filter_for_user(user)
        campaigns = campaigns.annotate(budget_last_updated_at=Max("budget_steps__created_at"))
        return campaigns

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        return queryset

    ordering_fields = [
        "obr_name",
        "cvdpv2_notified_at",
        "detection_status",
        "first_round_started_at",
        "last_round_started_at",
        "country__name",
        "last_budget_event__created_at",
        "last_budget_event__type",
        "last_budget_event__status",
        "budget_current_state_key",
    ]
    filterset_fields = {
        "last_budget_event__status": ["exact"],
        "country__name": ["exact"],
        "country__id": ["in"],
        "grouped_campaigns__id": ["in", "exact"],
        "obr_name": ["exact", "contains"],
        "cvdpv2_notified_at": ["gte", "lte", "range"],
        "created_at": ["gte", "lte", "range"],
        "rounds__started_at": ["gte", "lte", "range"],
        "budget_current_state_key": ["exact", "in"],
    }

    @action(detail=False, methods=["POST"], serializer_class=TransitionToSerializer)
    def transition_to(self, request):
        "Transition campaign to next state. Use multipart/form-data to send files"
        # data = request.data.dict()
        # data['links'] = request.data.getlist('links')
        data = request.data
        serializer = TransitionToSerializer(data=data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        budget_step = serializer.save()

        return Response({"result": "success", "id": budget_step.id}, status=status.HTTP_201_CREATED)

    @action(
        detail=False,
        methods=["POST"],
        serializer_class=TransitionOverrideSerializer,
        permission_classes=[HasPermission("iaso_polio_budget_admin")],
    )
    def override(self, request):
        "Transition campaign to next state. Use multipart/form-data to send files"
        data = request.data
        serializer = TransitionOverrideSerializer(data=data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        budget_step = serializer.save()

        return Response({"result": "success", "id": budget_step.id}, status=status.HTTP_201_CREATED)

    @action(
        detail=False,
        methods=["GET"],
        permission_classes=[HasPermission("iaso_polio_budget"), HasPermission("iaso_polio_budget_admin")],
    )
    def export_csv(self, request):
        countries = request.GET.get("country__id__in", None)
        current_state = request.GET.get("budget_current_state_key__in", None)
        search = request.GET.get("search", None)
        order = request.GET.get("order", "-cvdpv2_notified_at")
        campaigns = self.filter_queryset(self.get_queryset())
        # if countries:
        #     campaigns = campaigns.filter(country__id__in=countries.split(","))
        # if current_state:
        #     campaigns = campaigns.filter(budget_current_state_key__in=current_state.split(","))
        # if search:
        #     campaigns = campaigns.filter(
        #         Q(obr_name__icontains=search) | Q(epid__icontains=search) | Q(country__name__icontains=search)
        #     )
        campaigns = campaigns.order_by(order)
        date = datetime.now().strftime("%Y-%m-%d")
        fields = ["Campaign", "Country", "Status", "Notification date", "Latest step"]
        filename = f"campaigns_budget_list_{date}.csv"
        response = HttpResponse(
            content_type="txt/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
        writer = csv.writer(response)
        writer.writerow(fields)
        for c in campaigns:
            data_list = [
                c.obr_name,
                c.country.name,
                c.budget_current_state_label,
                c.cvdpv2_notified_at,
                c.budget_last_updated_at.strftime("%Y-%m-%d"),
            ]
            writer.writerow(data_list)
        return response


@swagger_auto_schema(tags=["budget"])
class BudgetStepViewSet(ModelViewSet):
    """
    Step on a campaign, to progress the budget workflow
    """

    # FIXME : add DELETE
    # filter perms on campaign
    ordering = "-created_at"

    def get_serializer_class(self) -> Type[serializers.BaseSerializer]:
        if self.request.method == "patch":
            return UpdateBudgetStepSerializer
        return BudgetStepSerializer

    permission_classes = [HasPermission("menupermissions.iaso_polio_budget")]  # type: ignore

    http_method_names = ["get", "head", "delete", "patch"]
    filter_backends = [
        filters.OrderingFilter,
        DeletionFilterBackend,
        DjangoFilterBackend,
    ]

    def get_queryset(self) -> QuerySet:
        return BudgetStep.objects.filter_for_user(self.request.user)

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        return queryset

    ordering_fields = [
        "campaign_id",
        "created_at",
        "created_by",
    ]
    filterset_fields = {
        "campaign_id": ["exact"],
        "transition_key": ["exact", "in"],
    }

    @action(detail=True, methods=["GET"], url_path="files/(?P<file_pk>[0-9]+)")
    def files(self, request, pk, file_pk):
        "Redirect to the static file"
        # Since on AWS S3 the signed url created (for the media upload files) are only valid a certain amount of time
        # This is endpoint is used to give a permanent url to the users.

        # Use the queryset to ensure the user has the proper access rights to this step
        # and keep down the url guessing.
        step: BudgetStep = self.get_queryset().get(pk=pk)
        stepFile: BudgetStepFile = get_object_or_404(step.files, pk=file_pk)
        url = stepFile.file.url
        return redirect(url, permanent=False)

    @action(detail=True, permission_classes=[permissions.IsAdminUser])
    def mail_template(self, request, pk):
        step = self.get_queryset().get(pk=pk)
        template_id = request.query_params.get("template_id")
        template = MailTemplate.objects.get(id=template_id)
        email_template = template.render_for_step(step, request.user, request)
        format = request.query_params.get("as", "all")
        if format == "html":
            html = email_template.alternatives[0][0]
        elif format == "txt":
            html = email_template.body
        elif format == "subject":
            html = email_template.subject
        else:
            html = email_template.message().as_string()

        return HttpResponse(html)


# noinspection PyMethodMayBeStatic
@swagger_auto_schema(tags=["budget"])
class WorkflowViewSet(ViewSet):
    """
    Info on the budge workflow

    This endpoint is currently used to show the possible state in the filter
    """

    permission_classes = [HasPermission("menupermissions.iaso_polio_budget")]  # type: ignore

    # At the moment I only implemented retrieve /current hardcode because we only support one workflow at the time
    # to keep the design simple, change if/when we want to support multiple workflow.

    def retrieve(self, request, pk="current"):
        try:
            workflow = get_workflow()
        except Exception as e:
            return Response({"error": "Error getting workflow", "details": str(e)})
        return Response(WorkflowSerializer(workflow).data)
