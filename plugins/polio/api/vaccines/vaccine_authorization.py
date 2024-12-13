import datetime
import datetime as dt
import itertools
from typing import Any

from django_filters.rest_framework import DjangoFilterBackend  # type: ignore
from drf_yasg.utils import swagger_auto_schema
from rest_framework import filters, serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from hat.menupermissions import models as permission
from iaso.api.common import (
    DeletionFilterBackend,
    GenericReadWritePerm,
    ModelViewSet,
    Paginator,
    TimestampField,
    Custom403Exception,
)
from iaso.models import OrgUnit
from plugins.polio.models import Group, VaccineAuthorization
from plugins.polio.settings import COUNTRY


def check_for_already_validated_authorization(status, country):
    if status == "VALIDATED":
        validated_vaccine_auth = VaccineAuthorization.objects.filter(
            status="VALIDATED", country=country, deleted_at__isnull=True
        )
        if validated_vaccine_auth:
            raise Custom403Exception({"error": f"A vaccine authorization is already validated for this country"})


class CountryForVaccineSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrgUnit
        fields = ["id", "name"]


class CountryField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        country = OrgUnit.objects.get(pk=value.pk)
        serializer = CountryForVaccineSerializer(country)
        return serializer.data


def handle_none_and_country(item, ordering):
    """
    This function handle the None cases to order the response of get_most_recent_authorizations
    and country nested dict.
    """
    if "country" in ordering:
        country_dict = item.get("country")
        country_name = country_dict.get("name")
        return country_name if country_name is not None else ""
    if "date" in ordering:
        date_field = item.get(ordering)
        return date_field if date_field else dt.date(1, 1, 1)
    if ordering != "date":
        item_value = item.get(ordering)
        return item_value if item_value is not None else float("inf")


class VaccineAuthorizationSerializer(serializers.ModelSerializer):
    country = CountryField(queryset=OrgUnit.objects.filter(org_unit_type__name="COUNTRY"))

    class Meta:
        model = VaccineAuthorization
        fields = [
            "id",
            "country",
            "start_date",
            "expiration_date",
            "created_at",
            "updated_at",
            "quantity",
            "status",
            "comment",
        ]
        read_only_fields = ["created_at", "updated_at"]
        created_at = TimestampField(read_only=True)
        updated_at = TimestampField(read_only=True)

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["account"] = user.iaso_profile.account
        status = validated_data.get("status")
        expiration_date = validated_data.get("expiration_date")
        start_date = validated_data.get("start_date")
        country = validated_data["country"]

        check_for_already_validated_authorization(status, country)

        # Check validity of the dates
        if expiration_date and expiration_date < datetime.date.today():
            raise serializers.ValidationError({"error": "expiration_date must be a future date."})
        if start_date and start_date > expiration_date:
            raise serializers.ValidationError({"error": "start_date must be before expiration_date."})

        return super().create(validated_data)

    def update(self, instance, validated_data):
        if validated_data.get("status") == "VALIDATED" and instance.status != "VALIDATED":
            country = instance.country
            check_for_already_validated_authorization("VALIDATED", country)

        return super().update(instance, validated_data)


class HasVaccineAuthorizationsPermissions(GenericReadWritePerm):
    read_perm = permission.POLIO_VACCINE_AUTHORIZATIONS_READ_ONLY
    write_perm = permission.POLIO_VACCINE_AUTHORIZATIONS_ADMIN


@swagger_auto_schema(tags=["vaccineauthorizations"])
class VaccineAuthorizationViewSet(ModelViewSet):
    """
    Vaccine Authorizations API
    list: /api/polio/vaccintauthorizations
    action: /api/polio/get_most_recent_authorizations
    """

    permission_classes = [HasVaccineAuthorizationsPermissions]
    filter_backends = [filters.OrderingFilter, DjangoFilterBackend, DeletionFilterBackend]
    results_key = "results"
    remove_results_key_if_paginated = True
    serializer_class = VaccineAuthorizationSerializer
    pagination_class = Paginator
    ordering_fields = ["status", "current_expiration_date", "next_expiration_date", "expiration_date", "quantity"]

    def get_queryset(self):
        user = self.request.user
        user_access_ou = OrgUnit.objects.filter_for_user_and_app_id(user, None)
        user_access_ou = user_access_ou.filter(org_unit_type__name=COUNTRY)
        country_id = self.request.query_params.get("country", None)
        queryset = VaccineAuthorization.objects.filter(account=user.iaso_profile.account, country__in=user_access_ou)
        block_country = self.request.query_params.get("block_country", None)
        search = self.request.query_params.get("search", None)
        auth_status = self.request.query_params.get("auth_status", None)

        if country_id:
            queryset = queryset.filter(country__pk=country_id)
        if block_country:
            block_country = block_country.split(",")
            block_country = Group.objects.filter(pk__in=block_country)
            org_units = [
                ou_queryset
                for ou_queryset in [
                    ou_group_queryset for ou_group_queryset in [country.org_units.all() for country in block_country]
                ]
            ]
            ou_pk_list = []
            for ou_q in org_units:
                for ou in ou_q:
                    ou_pk_list.append(ou.pk)
            queryset = queryset.filter(country__pk__in=ou_pk_list)
        if search:
            queryset = queryset.filter(country__name__icontains=search)
        if auth_status:
            auth_status = auth_status.split(",")
            queryset = queryset.filter(status__in=auth_status)

        return queryset

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        # Casting both the country id sent by the front-end and teh org unit id as strings
        # Because otherwise we get bugs left and right. This was done as part of a hotfix and should be cleaned up
        # POLIO-1247
        country = str(self.request.data.get("country", None))
        if not self.request.user.is_superuser:
            if country not in [
                str(ou.id) for ou in OrgUnit.objects.filter_for_user_and_app_id(self.request.user, None)
            ]:
                raise serializers.ValidationError({"Error": "You don't have access to this org unit."})

        return super().create(request)

    @action(detail=False, methods=["GET"])
    def get_most_recent_authorizations(self, request):
        """
        Compute the most recent vaccine authorization per country.
        """
        # Filters are done after calculation as all the status are required in order to compute the correct response
        user = self.request.user
        user_access_ou = OrgUnit.objects.filter_for_user_and_app_id(user, None)
        user_access_ou = user_access_ou.filter(org_unit_type__name=COUNTRY)
        queryset = VaccineAuthorization.objects.filter(account=user.iaso_profile.account, country__in=user_access_ou)
        auth_status = self.request.query_params.get("auth_status", None)
        block_country = self.request.query_params.get("block_country", None)
        country_list = []
        response = []

        ordering = request.query_params.get("order", None)

        for auth in queryset:
            if auth.country not in country_list:
                country_list.append(auth.country)

        for country in country_list:
            last_validated_or_expired = (
                queryset.filter(country=country, status__in=["VALIDATED", "EXPIRED"], deleted_at__isnull=True)
                .order_by("-expiration_date")
                .first()
            )

            next_expiration_auth = (
                queryset.filter(country=country, status__in=["ONGOING", "SIGNATURE"], deleted_at__isnull=True)
                .order_by("-expiration_date")
                .first()
            )

            last_entry = queryset.filter(country=country, deleted_at__isnull=True).last()

            last_entry_date_check = VaccineAuthorization.objects.filter(
                country=country, account=self.request.user.iaso_profile.account, deleted_at__isnull=True
            ).last()

            if last_entry_date_check and last_entry:
                if last_entry_date_check.expiration_date > last_entry.expiration_date:
                    return Response(response)

            if last_validated_or_expired and next_expiration_auth:
                vacc_auth = {
                    "id": last_entry.id,
                    "country": {
                        "id": last_entry.country.pk,
                        "name": last_entry.country.name,
                    },
                    "start_date": last_validated_or_expired.start_date,
                    "current_expiration_date": last_validated_or_expired.expiration_date,
                    "next_expiration_date": (
                        next_expiration_auth.expiration_date
                        if next_expiration_auth.expiration_date > last_validated_or_expired.expiration_date
                        else None
                    ),
                    "quantity": last_validated_or_expired.quantity,
                    "status": last_entry.status,
                    "comment": last_entry.comment,
                }

                response.append(vacc_auth)

            if last_validated_or_expired is None and next_expiration_auth:
                vacc_auth = {
                    "id": last_entry.id,
                    "country": {
                        "id": last_entry.country.pk,
                        "name": last_entry.country.name,
                    },
                    "start_date": last_entry.start_date,
                    "current_expiration_date": None,
                    "next_expiration_date": next_expiration_auth.expiration_date,
                    "quantity": None,
                    "status": last_entry.status,
                    "comment": last_entry.comment,
                }

                response.append(vacc_auth)

            if last_validated_or_expired and next_expiration_auth is None:
                vacc_auth = {
                    "id": last_validated_or_expired.id,
                    "country": {
                        "id": last_validated_or_expired.country.pk,
                        "name": last_validated_or_expired.country.name,
                    },
                    "start_date": last_validated_or_expired.start_date,
                    "current_expiration_date": last_validated_or_expired.expiration_date,
                    "next_expiration_date": None,
                    "quantity": last_validated_or_expired.quantity,
                    "status": last_validated_or_expired.status,
                    "comment": last_validated_or_expired.comment,
                }

                response.append(vacc_auth)

        if auth_status:
            response = [entry for entry in response if entry["status"] in auth_status.split(",")]

        if block_country:
            block_country = block_country.split(",")
            block_country = Group.objects.filter(pk__in=block_country)
            org_units_ids = [country.org_units.all().values_list("pk", flat=True) for country in block_country]
            ou_pk_list = set(itertools.chain.from_iterable(org_units_ids))
            response = [entry for entry in response if entry["country"]["id"] in ou_pk_list]

        if ordering:
            if ordering[0] == "-":
                response = sorted(response, key=lambda x: handle_none_and_country(x, ordering[1:]), reverse=True)
            else:
                response = sorted(response, key=lambda x: handle_none_and_country(x, ordering))
        page = self.paginate_queryset(response)

        if page:
            return self.get_paginated_response(page)

        return Response(response)
