import django_filters

from django.db.models import QuerySet

from rest_framework import filters, status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from iaso.api.common import Paginator

from plugins.polio.api.chronogram.filters import ChronogramFilter, ChronogramTaskFilter
from plugins.polio.api.chronogram.permissions import HasChronogramPermission
from plugins.polio.api.chronogram.serializers import (
    ChronogramSerializer,
    ChronogramTaskSerializer,
    ChronogramTemplateTaskSerializer,
    ChronogramCreateSerializer,
)
from plugins.polio.models import Campaign, Chronogram, ChronogramTask, ChronogramTemplateTask, Round


class ChronogramPagination(Paginator):
    page_size = 20


class ChronogramViewSet(viewsets.ModelViewSet):
    filter_backends = [filters.OrderingFilter, django_filters.rest_framework.DjangoFilterBackend]
    filterset_class = ChronogramFilter
    http_method_names = ["get", "options", "head", "post", "trace"]
    pagination_class = ChronogramPagination
    permission_classes = [HasChronogramPermission]
    serializer_class = ChronogramSerializer

    def get_queryset(self) -> QuerySet:
        user = self.request.user
        rounds_ids = Campaign.polio_objects.filter_for_user(user).values_list("rounds", flat=True)
        return (
            Chronogram.objects.valid()
            .filter(round_id__in=rounds_ids)
            .select_related("round__campaign", "created_by", "updated_by")
            .prefetch_related("tasks__user_in_charge", "tasks__created_by", "tasks__updated_by")
            .order_by("created_at")
        )

    def create(self, request, *args, **kwargs):
        """
        Create a `Chronogram` and populate it with `ChronogramTemplateTask` objects (if any).
        """
        serializer = ChronogramCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save(created_by=self.request.user)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=False, methods=["GET"])
    def available_rounds_for_create(self, request):
        """
        Returns all available rounds that can be used to create a new `Chronogram`.
        """
        user_campaigns = Campaign.polio_objects.filter_for_user(self.request.user).filter(country__isnull=False)
        available_rounds = (
            Round.objects.filter(chronogram__isnull=True, campaign__in=user_campaigns)
            .select_related("campaign__country")
            .order_by("campaign__country__name", "campaign__obr_name", "number")
            .only(
                "id",
                "number",
                "campaign_id",
                "campaign__obr_name",
                "campaign__country_id",
                "campaign__country__name",
                "target_population",
            )
        )
        return Response(available_rounds.as_ui_dropdown_data(), status=status.HTTP_200_OK)


class ChronogramTaskViewSet(viewsets.ModelViewSet):
    filter_backends = [filters.OrderingFilter, django_filters.rest_framework.DjangoFilterBackend]
    filterset_class = ChronogramTaskFilter
    pagination_class = ChronogramPagination
    permission_classes = [HasChronogramPermission]
    serializer_class = ChronogramTaskSerializer

    def get_queryset(self) -> QuerySet:
        user = self.request.user
        campaigns = Campaign.polio_objects.filter_for_user(user)
        return (
            ChronogramTask.objects.filter(chronogram__round__campaign__in=campaigns)
            .select_related("chronogram__round", "user_in_charge", "created_by", "updated_by")
            .order_by("created_at")
        )

    def perform_create(self, serializer):
        serializer.validated_data["created_by"] = self.request.user
        serializer.save()

    def perform_update(self, serializer):
        serializer.validated_data["updated_by"] = self.request.user
        serializer.save()


class ChronogramTemplateTaskViewSet(viewsets.ModelViewSet):
    filter_backends = [filters.OrderingFilter, django_filters.rest_framework.DjangoFilterBackend]
    pagination_class = ChronogramPagination
    permission_classes = [HasChronogramPermission]
    serializer_class = ChronogramTemplateTaskSerializer

    def get_queryset(self) -> QuerySet:
        account = self.request.user.iaso_profile.account
        return (
            ChronogramTemplateTask.objects.valid()
            .filter(account=account)
            .select_related("created_by", "updated_by")
            .order_by("created_at")
        )

    def perform_create(self, serializer):
        serializer.validated_data["created_by"] = self.request.user
        serializer.save()

    def perform_update(self, serializer):
        serializer.validated_data["updated_by"] = self.request.user
        serializer.save()
