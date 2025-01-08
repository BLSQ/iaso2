import django_filters
from django.conf import settings
from django.db.models import Q
from django.db.models.query import QuerySet
from django.utils.translation import gettext_lazy as _
from iaso.models.data_source import SourceVersion
from rest_framework.exceptions import ValidationError
from iaso.api.common import parse_comma_separated_numeric_values
from iaso.models import OrgUnit, OrgUnitChangeRequest
from iaso.models.payments import PaymentStatuses


class MobileOrgUnitChangeRequestListFilter(django_filters.rest_framework.FilterSet):
    last_sync = django_filters.IsoDateTimeFilter(field_name="updated_at", lookup_expr="gte")

    class Meta:
        model = OrgUnitChangeRequest
        fields = []


class OrgUnitChangeRequestListFilter(django_filters.rest_framework.FilterSet):
    org_unit_id = django_filters.NumberFilter(field_name="org_unit_id", label=_("Org unit ID"))
    org_unit_type_id = django_filters.CharFilter(method="filter_org_unit_type_id", label=_("Org unit type ID"))
    parent_id = django_filters.NumberFilter(method="filter_parent_id", label=_("Parent ID"))
    groups = django_filters.CharFilter(method="filter_groups", label=_("Groups IDs (comma-separated)"))
    project = django_filters.NumberFilter(field_name="org_unit__org_unit_type__projects", label=_("Project ID"))
    created_at = django_filters.DateFromToRangeFilter()
    data_source_synchronization_id = django_filters.CharFilter(
        field_name="data_source_synchronization_id", label=_("Data source synchronization ID")
    )

    forms = django_filters.CharFilter(method="filter_forms", label=_("Forms IDs (comma-separated)"))
    users = django_filters.CharFilter(method="filter_users", label=_("Users IDs (comma-separated)"))
    user_roles = django_filters.CharFilter(method="filter_user_roles", label=_("User roles IDs (comma-separated)"))
    with_location = django_filters.CharFilter(method="filter_with_location", label=_("With or without location"))
    status = django_filters.CharFilter(method="filter_status", label=_("Status (comma-separated)"))
    projects = django_filters.CharFilter(method="filter_projects", label=_("Projects IDs (comma-separated)"))
    payment_status = django_filters.CharFilter(method="filter_payment_status", label=_("Payment status"))
    payment_ids = django_filters.CharFilter(method="filter_payments", label=_("Payment IDs (comma-separated)"))
    potential_payment_ids = django_filters.CharFilter(
        method="filter_potential_payments", label=_("Potential Payment IDs (comma-separated)")
    )
    source_version_id = django_filters.NumberFilter(field_name="org_unit__version", label=_("Source version ID"))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.form.fields["created_at"].fields[0].input_formats = settings.API_DATE_INPUT_FORMATS
        self.form.fields["created_at"].fields[-1].input_formats = settings.API_DATE_INPUT_FORMATS

    class Meta:
        model = OrgUnitChangeRequest
        fields = []

    def filter_parent_id(self, queryset: QuerySet, _, value: str) -> QuerySet:
        try:
            parent = OrgUnit.objects.get(id=value)
            parent_qs = OrgUnit.objects.filter(id=parent.id)
            descendants_qs = OrgUnit.objects.hierarchy(parent_qs).values_list("id", flat=True)
            return queryset.filter(Q(old_parent_id__in=descendants_qs) | Q(new_parent_id__in=descendants_qs))
        except OrgUnit.DoesNotExist:
            raise ValidationError({"parent_id": [f"OrgUnit with id {value} does not exist."]})

    def filter_org_unit_type_id(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        org_unit_type_ids = parse_comma_separated_numeric_values(value, name)
        return queryset.filter(
            Q(old_org_unit_type__id__in=org_unit_type_ids) | Q(new_org_unit_type__id__in=org_unit_type_ids)
        )

    def filter_groups(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        groups_ids = parse_comma_separated_numeric_values(value, name)
        return queryset.filter(Q(old_groups__in=groups_ids) | Q(new_groups__in=groups_ids))

    def filter_projects(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        projects_ids = parse_comma_separated_numeric_values(value, name)
        return queryset.filter(
            Q(old_org_unit_type__projects__in=projects_ids) | Q(new_org_unit_type__projects__in=projects_ids)
        )

    def filter_forms(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        forms_ids = parse_comma_separated_numeric_values(value, name)
        return queryset.filter(
            Q(old_reference_instances__form_id__in=forms_ids) | Q(new_reference_instances__form_id__in=forms_ids)
        )

    def filter_users(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        users_ids = parse_comma_separated_numeric_values(value, name)
        return queryset.filter(Q(created_by_id__in=users_ids) | Q(updated_by__in=users_ids))

    def filter_user_roles(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        users_roles_ids = parse_comma_separated_numeric_values(value, name)
        return queryset.filter(
            Q(created_by__iaso_profile__user_roles__id__in=users_roles_ids)
            | Q(updated_by__iaso_profile__user_roles__id__in=users_roles_ids)
        )

    def filter_status(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        if value:
            statuses = value.split(",")
            queryset = queryset.filter(status__in=statuses)
        return queryset

    def filter_with_location(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        """
        `value` is intended to be boolean string "true" or "false".
        """

        has_location = Q(new_location__isnull=False) | Q(old_location__isnull=False)

        if value == "true":
            queryset = queryset.filter(has_location)

        if value == "false":
            queryset = queryset.exclude(has_location)

        return queryset

    def filter_payment_status(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        """
        `value` is one of `PaymentStatuses`
        """

        if value not in PaymentStatuses.values:
            raise ValidationError(
                f"Expected payment status to be one of {','.join(PaymentStatuses.values)}, got {value}"
            )
        if value == PaymentStatuses.PENDING:
            pending_filter = (
                Q(payment__isnull=True)
                & (Q(potential_payment__isnull=False) | Q(status=OrgUnitChangeRequest.Statuses.APPROVED.value))
            ) | Q(payment__status=PaymentStatuses.PENDING)
            return queryset.filter(pending_filter)
        else:
            return queryset.filter(payment__status=value)

    # This filter is used when redirecting from potential payments to see related change requests. It is not otherwise visible in the UI
    def filter_potential_payments(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        potential_payment_ids = parse_comma_separated_numeric_values(value, name)
        return queryset.filter(potential_payment__in=potential_payment_ids)

    # This filter is used when redirecting from payment lots to see related change requests. It is not otherwise visible in the UI
    def filter_payments(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        payment_ids = parse_comma_separated_numeric_values(value, name)
        return queryset.filter(payment__in=payment_ids)
