from django.db.models import Count
import django_filters
from rest_framework.exceptions import NotFound
from hat.menupermissions import models as permission
from iaso.api.common import (
    HasPermission,
    ModelViewSet,
)
from iaso.api.payments.filters import PotentialPaymentsListFilter
from iaso.models import Payment, OrgUnitChangeRequest, PotentialPayment
from rest_framework import filters, permissions
from .serializers import PotentialPaymentSerializer


class PotentialPaymentsViewSet(ModelViewSet):
    """Potential Payments API

    This API is restricted to authenticated users.

    GET /api/potential_payments/
    """

    permission_classes = [permissions.IsAuthenticated, HasPermission(permission.PAYMENTS)]
    filter_backends = [filters.OrderingFilter, django_filters.rest_framework.DjangoFilterBackend]
    ordering_fields = [
        "user__username",
        "user__last_name",
        "user__first_name",
        "created_at",
        "updated_at",
        "status",
        "created_by__username",
        "updated_by__username",
        "change_requests",
    ]
    serializer_class = PotentialPaymentSerializer
    filterset_class = PotentialPaymentsListFilter

    results_key = "results"
    http_method_names = ["get", "head", "options", "trace"]

    def get_queryset(self):
        queryset = PotentialPayment.objects.all()
        queryset = queryset.prefetch_related(
            "change_requests",
        )
        queryset = queryset.filter(
            change_requests__created_by__iaso_profile__account=self.request.user.iaso_profile.account
        ).distinct()

        return queryset

    def retrieve(self, request, *args, **kwargs):
        raise NotFound("Retrieve operation is not allowed.")

    def list(self, request):
        orders = request.GET.get("order", "user__last_name").split(",")
        # Clear out old potential payments
        PotentialPayment.objects.all().delete()

        # Get all users who have approved change requests
        users_with_change_requests = (
            OrgUnitChangeRequest.objects.filter(status=OrgUnitChangeRequest.Statuses.APPROVED)
            .values("created_by")
            .annotate(num_requests=Count("created_by"))
            .filter(num_requests__gt=0)
        )

        for user in users_with_change_requests:
            # Get all approved change requests for this user
            change_requests = OrgUnitChangeRequest.objects.filter(
                created_by_id=user["created_by"], status=OrgUnitChangeRequest.Statuses.APPROVED
            )

            # Create a new PotentialPayment instance for each user
            potential_payment = PotentialPayment.objects.create(
                user_id=user["created_by"],
            )
            # For each change request, check if a Payment already exists
            for change_request in change_requests:
                if not Payment.objects.filter(change_requests__id=change_request.id).exists():
                    # If no Payment exists for the change request, add it to the PotentialPayment instance
                    potential_payment.change_requests.add(change_request)
            potential_payment.save()

        # Use the built-in list method of ModelViewSet which handles ordering and pagination
        return super().list(request, queryset=PotentialPayment.objects.all().order_by(*orders))
