import datetime
import json
import math
import os
from collections import defaultdict
from datetime import date
from typing import Any, Optional, Tuple, Union
from uuid import uuid4

import django.db.models.manager
import pandas as pd
from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.postgres.fields import ArrayField
from django.core.files.base import File
from django.core.serializers.json import DjangoJSONEncoder
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.expressions import RawSQL
from django.db.models import Q, QuerySet, Sum, Subquery
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.utils.module_loading import import_string
from django.utils.translation import gettext as _
from gspread.utils import extract_id_from_url  # type: ignore
from storages.backends.s3boto3 import S3Boto3Storage
from translated_fields import TranslatedField

from beanstalk_worker import task_decorator
from iaso.models import Group, OrgUnit
from iaso.models.base import Account, Task
from iaso.models.entity import UserNotAuthError
from iaso.models.microplanning import Team
from iaso.utils import slugify_underscore
from iaso.utils.models.soft_deletable import DefaultSoftDeletableManager, SoftDeletableModel
from plugins.polio.preparedness.parser import open_sheet_by_url
from plugins.polio.preparedness.spread_cache import CachedSpread

VIRUSES = [
    ("PV1", _("PV1")),
    ("PV2", _("PV2")),
    ("PV3", _("PV3")),
    ("cVDPV2", _("cVDPV2")),
    ("WPV1", _("WPV1")),
    ("PV1 & cVDPV2", _("PV1 & cVDPV2")),
    ("cVDPV1 & cVDPV2", _("cVDPV1 & cVDPV2")),
]

VACCINES = [
    ("mOPV2", _("mOPV2")),
    ("nOPV2", _("nOPV2")),
    ("bOPV", _("bOPV")),
    ("nOPV2 & bOPV", _("nOPV2 & bOPV")),
]

INDIVIDUAL_VACCINES = [
    ("mOPV2", _("mOPV2")),
    ("nOPV2", _("nOPV2")),
    ("bOPV", _("bOPV")),
]

DOSES_PER_VIAL = {
    "mOPV2": 20,
    "nOPV2": 50,
    "bOPV": 20,
}

LANGUAGES = [
    ("FR", "Français"),
    ("EN", "English"),
    ("PT", "Português"),
]

RESPONSIBLES = [
    ("WHO", _("WHO")),
    ("UNICEF", _("UNICEF")),
    ("NAT", _("National")),
    ("MOH", _("MOH")),
    ("PROV", _("PROVINCE")),
    ("DIST", _("District")),
]

STATUS = [
    ("PENDING", _("Pending")),
    ("ONGOING", _("Ongoing")),
    ("FINISHED", _("Finished")),
]

RA_BUDGET_STATUSES = [
    ("APPROVED", _("Approved")),
    ("TO_SUBMIT", _("To Submit")),
    ("SUBMITTED", _("Submitted")),
    ("REVIEWED", _("Reviewed by RRT")),
]

PREPAREDNESS_SYNC_STATUS = [
    ("QUEUED", _("Queued")),
    ("ONGOING", _("Ongoing")),
    ("FAILURE", _("Failed")),
    ("FINISHED", _("Finished")),
]

PAYMENT = [("DIRECT", _("Direct")), ("DFC", _("DFC")), ("MOBILE_PAYMENT", _("Mobile Payment"))]


class DelayReasons(models.TextChoices):
    INITIAL_DATA = "INITIAL_DATA", _("initial_data")
    ENCODING_ERROR = "ENCODING_ERROR", _("encoding_error")
    PUBLIC_HOLIDAY = "PUBLIC_HOLIDAY", _("public_holday")
    OTHER_ACTIVITIES = "OTHER_ACTIVITIES", _("other_activities")
    MOH_DECISION = "MOH_DECISION", _("moh_decision")
    CAMPAIGN_SYNCHRONIZATION = "CAMPAIGN_SYNCHRONIZATION", _("campaign_synchronization")
    PREPAREDNESS_LEVEL_NOT_REACHED = "PREPAREDNESS_LEVEL_NOT_REACHED", _("preparedness_level_not_reached")
    FUNDS_NOT_RECEIVED_OPS_LEVEL = "FUNDS_NOT_RECEIVED_OPS_LEVEL", _("funds_not_received_ops_level")
    FUNDS_NOT_ARRIVED_IN_COUNTRY = "FUNDS_NOT_ARRIVED_IN_COUNTRY", _("funds_not_arrived_in_country")
    VACCINES_NOT_DELIVERED_OPS_LEVEL = "VACCINES_NOT_DELIVERED_OPS_LEVEL", _("vaccines_not_delivered_ops_level")
    VACCINES_NOT_ARRIVED_IN_COUNTRY = "VACCINES_NOT_ARRIVED_IN_COUNTRY", _("vaccines_not_arrived_in_country")
    SECURITY_CONTEXT = "SECURITY_CONTEXT", _("security_context")
    CAMPAIGN_MOVED_FORWARD_BY_MOH = "CAMPAIGN_MOVED_FORWARD_BY_MOH", _("campaign_moved_forward_by_moh")
    VRF_NOT_SIGNED = "VRF_NOT_SIGNED", _("vrf_not_signed")
    FOUR_WEEKS_GAP_BETWEEN_ROUNDS = "FOUR_WEEKS_GAP_BETWEEN_ROUNDS", _("four_weeks_gap_betwenn_rounds")
    OTHER_VACCINATION_CAMPAIGNS = "OTHER_VACCINATION_CAMPAIGNS", _("other_vaccination_campaigns")
    PENDING_LIQUIDATION_OF_PREVIOUS_SIA_FUNDING = "PENDING_LIQUIDATION_OF_PREVIOUS_SIA_FUNDING", _(
        "pending_liquidation_of_previous_sia_funding"
    )


class AgeChoices(models.TextChoices):
    YEARS = "YEARS", _("years")
    MONTHS = "MONTHS", _("months")


def make_group_round_scope():
    return Group.objects.create(name="hidden roundScope")


class RoundScope(models.Model):
    "Scope (selection of orgunit) for a round and vaccines"

    group = models.OneToOneField(
        Group, on_delete=models.CASCADE, related_name="roundScope", default=make_group_round_scope
    )
    round = models.ForeignKey("Round", on_delete=models.CASCADE, related_name="scopes")

    vaccine = models.CharField(max_length=12, choices=VACCINES, blank=True)

    class Meta:
        unique_together = [("round", "vaccine")]
        ordering = ["round", "vaccine"]


def make_group_campaign_scope():
    return Group.objects.create(name="hidden campaignScope")


class CampaignScope(models.Model):
    """Scope (selection of orgunit) for a campaign and vaccines"""

    group = models.OneToOneField(
        Group, on_delete=models.CASCADE, related_name="campaignScope", default=make_group_campaign_scope
    )
    campaign = models.ForeignKey("Campaign", on_delete=models.CASCADE, related_name="scopes")
    vaccine = models.CharField(max_length=12, choices=VACCINES, blank=True)

    class Meta:
        unique_together = [("campaign", "vaccine")]
        ordering = ["campaign", "vaccine"]


class RoundDateHistoryEntryQuerySet(models.QuerySet):
    def filter_for_user(self, user: Union[User, AnonymousUser]):
        from plugins.polio.models import Campaign

        campaigns = Campaign.objects.filter_for_user(user)  # type: ignore
        return self.filter(round__campaign__in=campaigns)


class RoundDateHistoryEntry(models.Model):
    objects = RoundDateHistoryEntryQuerySet.as_manager()
    previous_started_at = models.DateField(null=True, blank=True)
    previous_ended_at = models.DateField(null=True, blank=True)
    started_at = models.DateField(null=True, blank=True)
    ended_at = models.DateField(null=True, blank=True)
    reason_for_delay = models.ForeignKey(
        "ReasonForDelay", on_delete=models.PROTECT, null=True, blank=True, related_name="round_history_entries"
    )
    round = models.ForeignKey("Round", on_delete=models.CASCADE, related_name="datelogs", null=True, blank=True)
    modified_by = models.ForeignKey("auth.User", on_delete=models.PROTECT, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class ReasonForDelay(SoftDeletableModel):
    name = TranslatedField(models.CharField(_("name"), max_length=200), {"fr": {"blank": True}})
    # key_name is necessary for the current implementation of powerBi dashboards
    # and for the front-end to be able to prevent users from selecting "INITIAL_DATA"
    # when updating round dates
    key_name = models.CharField(blank=True, max_length=200, validators=[RegexValidator(r"^[A-Z_]+$")])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    account = models.ForeignKey(Account, models.CASCADE, related_name="reasons_for_delay")

    class Meta:
        # This will prevent sharing reasons across accounts, but it can be annoying if 2 accounts need INITIAL_DATA
        unique_together = ["key_name", "account"]

    def __str__(self):
        return self.name


class RoundQuerySet(models.QuerySet):
    def as_ui_dropdown_data(self):
        """
        Returns a data structure suitable to build dependent select dropdowns in the UI:
        {
            "countries": [
                {"value": 1, "label": "Niger"}
            ],
            "campaigns": [
                {"value": "e5a1209b-8881-4b66-82a0-429a53dbc94b", "label": "nopv2", "country_id": 1}
            ],
            "rounds": [
                {"value": 1, "label": 1, "campaign_id": "e5a1209b-8881-4b66-82a0-429a53dbc94b"}
            ]
        }
        """
        data = {"countries": {}, "campaigns": {}, "rounds": []}

        for rnd in self:
            campaign_uuid = str(rnd.campaign_id)
            data["countries"].setdefault(
                rnd.campaign.country_id,
                {"value": rnd.campaign.country_id, "label": rnd.campaign.country.name},
            )
            data["campaigns"].setdefault(
                campaign_uuid,
                {"value": campaign_uuid, "label": rnd.campaign.obr_name, "country_id": rnd.campaign.country_id},
            )
            data["rounds"].append(
                {
                    "value": rnd.id,
                    "label": rnd.number,
                    "campaign_id": campaign_uuid,
                    "target_population": rnd.target_population,
                }
            )

        data["countries"] = data["countries"].values()
        data["campaigns"] = data["campaigns"].values()
        return data

    def filter_by_vaccine_name(self, vaccine_name):
        return (
            self.select_related("campaign")
            .prefetch_related("scopes", "campaign__scopes")
            .filter(
                (Q(campaign__separate_scopes_per_round=False) & Q(campaign__scopes__vaccine=vaccine_name))
                | (Q(campaign__separate_scopes_per_round=True) & Q(scopes__vaccine=vaccine_name))
            )
        )


def make_group_subactivity_scope():
    return Group.objects.create(name="hidden subactivityScope")


class SubActivityScope(models.Model):
    "Scope (selection of orgunit) for a SubActivity and vaccines"

    group = models.OneToOneField(
        Group, on_delete=models.CASCADE, related_name="subactivityScope", default=make_group_subactivity_scope
    )
    subactivity = models.ForeignKey("SubActivity", on_delete=models.CASCADE, related_name="scopes")

    vaccine = models.CharField(max_length=12, choices=VACCINES, blank=True)


AGE_UNITS = [
    ("m", "Months"),
    ("y", "Years"),
]


class SubActivity(models.Model):
    round = models.ForeignKey("Round", related_name="sub_activities", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    age_unit = models.CharField(max_length=3, choices=AGE_UNITS, null=True, blank=True)
    age_min = models.IntegerField(null=True, blank=True)
    age_max = models.IntegerField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    im_started_at = models.DateField(null=True, blank=True)
    im_ended_at = models.DateField(null=True, blank=True)
    lqas_started_at = models.DateField(null=True, blank=True)
    lqas_ended_at = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "subactivities"

    def __str__(self):
        return self.name

    @property
    def vaccine_list(self):
        all_vaccines = self.scopes.all().values_list("vaccine", flat=True)
        vaccines = set()
        vaccines.update(all_vaccines)
        return sorted(list(vaccines))

    @property
    def vaccine_names(self):
        return ", ".join(self.vaccine_list)

    @property
    def single_vaccine_list(self):
        vaccines = set(self.vaccine_list)
        return sorted(list(Campaign.split_combined_vaccines(vaccines)))

    @property
    def single_vaccine_names(self):
        return ", ".join(self.single_vaccine_list)


class Round(models.Model):
    class Meta:
        ordering = ["number", "started_at"]

    # With the current situation/UI, all rounds must have a start date. However, there might be legacy campaigns/rounds
    # floating around in production, and therefore consumer code must assume that this field might be NULL
    started_at = models.DateField(null=True, blank=True)
    number = models.IntegerField(null=True, blank=True)
    campaign = models.ForeignKey("Campaign", related_name="rounds", on_delete=models.PROTECT, null=True)
    budget_process = models.ForeignKey(
        "BudgetProcess", related_name="rounds", on_delete=models.SET_NULL, null=True, blank=True
    )
    # With the current situation/UI, all rounds must have an end date. However, there might be legacy campaigns/rounds
    # floating around in production, and therefore consumer code must assume that this field might be NULL
    ended_at = models.DateField(null=True, blank=True)

    age_min = models.IntegerField(null=True, blank=True)
    age_max = models.IntegerField(null=True, blank=True)
    age_type = models.TextField(null=True, blank=True, choices=AgeChoices.choices)

    mop_up_started_at = models.DateField(null=True, blank=True)
    mop_up_ended_at = models.DateField(null=True, blank=True)
    im_started_at = models.DateField(null=True, blank=True)
    im_ended_at = models.DateField(null=True, blank=True)
    lqas_started_at = models.DateField(null=True, blank=True)
    lqas_ended_at = models.DateField(null=True, blank=True)
    target_population = models.IntegerField(null=True, blank=True)
    doses_requested = models.IntegerField(null=True, blank=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.0, null=True, blank=True)
    im_percentage_children_missed_in_household = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    im_percentage_children_missed_out_household = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    im_percentage_children_missed_in_plus_out_household = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    awareness_of_campaign_planning = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    main_awareness_problem = models.CharField(max_length=255, null=True, blank=True)
    lqas_district_passing = models.IntegerField(null=True, blank=True)
    lqas_district_failing = models.IntegerField(null=True, blank=True)
    is_test = models.BooleanField(default=False)

    # Preparedness
    preparedness_spreadsheet_url = models.URLField(null=True, blank=True)
    preparedness_sync_status = models.CharField(max_length=10, default="FINISHED", choices=PREPAREDNESS_SYNC_STATUS)
    # Vaccine management
    date_signed_vrf_received = models.DateField(null=True, blank=True)
    date_destruction = models.DateField(null=True, blank=True)
    vials_destroyed = models.IntegerField(null=True, blank=True)
    reporting_delays_hc_to_district = models.IntegerField(null=True, blank=True)
    reporting_delays_district_to_region = models.IntegerField(null=True, blank=True)
    reporting_delays_region_to_national = models.IntegerField(null=True, blank=True)
    forma_reception = models.DateField(null=True, blank=True)
    forma_missing_vials = models.IntegerField(null=True, blank=True)
    forma_usable_vials = models.IntegerField(null=True, blank=True)
    forma_unusable_vials = models.IntegerField(null=True, blank=True)
    forma_date = models.DateField(null=True, blank=True)
    forma_comment = models.TextField(blank=True, null=True)
    percentage_covered_target_population = models.IntegerField(null=True, blank=True)
    # End of vaccine management

    objects = models.Manager.from_queryset(RoundQuerySet)()

    def delete(self, *args, **kwargs):
        # Explicitly delete groups related to the round's scopes, because the cascade deletion won't work reliably
        Group.objects.filter(roundScope__isnull=False).filter(
            roundScope__id__in=Subquery(self.scopes.all().values_list("id", flat=True))
        ).delete()

        # Call the parent class's delete() method to proceed with deleting the Round
        # The scope will be deleted by Django's cascading
        super().delete(*args, **kwargs)

    def add_chronogram(self):
        """
        Create a "standard chronogram" for all upcoming rounds of a campaign.
        See POLIO-1781.
        """
        from plugins.polio.models import ChronogramTemplateTask

        if isinstance(self.started_at, datetime.datetime):
            self.started_at = self.started_at.date()

        if (
            self.started_at
            and isinstance(self.started_at, datetime.date)
            and self.started_at >= timezone.now().date()
            and self.campaign
            and self.campaign.has_polio_type
            and not self.chronograms.valid().exists()
        ):
            ChronogramTemplateTask.objects.create_chronogram(round=self, created_by=None, account=self.campaign.account)

    def get_item_by_key(self, key):
        return getattr(self, key)

    @staticmethod
    def is_round_over(round):
        if not round.ended_at:
            return False
        return round.ended_at < date.today()

    @property
    def actual_scopes(self):
        """The scopes that actually apply to the round.
        Can be used to get the shapes of the actual scope, but not the vaccines, since sub-activities are not included.
        To get all vaccines applicable for the round, use vaccines_list_extended or vaccine_names_extended properties.
        Would need manual serializing for use in APIs because the CampaignScope and RoundScope are different models
        """
        if self.campaign.separate_scopes_per_round:
            return self.scopes
        else:
            return self.campaign.scopes

    @property
    def vaccine_list(self):
        """Vaccines used for the round. Not including sub-activities"""
        vaccines = set()
        if self.campaign.separate_scopes_per_round:
            round_vaccines = RoundScope.objects.filter(
                round=self, group__org_units__isnull=False, vaccine__isnull=False
            ).values_list("vaccine", flat=True)

            vaccines.update(round_vaccines)

        else:
            campaign_vaccines = CampaignScope.objects.filter(
                campaign=self.campaign, group__org_units__isnull=False, vaccine__isnull=False
            ).values_list("vaccine", flat=True)

            vaccines.update(campaign_vaccines)

        return sorted(list(vaccines))

    @property
    def single_vaccine_list(self):
        vaccines = set(self.vaccine_list)
        return sorted(list(Campaign.split_combined_vaccines(vaccines)))

    @property
    def vaccine_names(self):
        """Vaccines used for the round, in string form for easy use in API. Not including sub-activities"""
        return ", ".join(sorted(list(self.vaccine_list)))

    @property
    def single_vaccine_names(self):
        """Vaccines used for the round, splitting type bOPV & nOPV2 into it's component vaccines.
        In string form for easy use in API.
        Not including sub-activities"""
        return ", ".join(sorted(list(self.single_vaccine_list)))

    @property
    def subactivities_vaccine_list(self):
        vaccines = set()

        subactivity_vaccines = SubActivityScope.objects.filter(
            subactivity__round=self, group__org_units__isnull=False, vaccine__isnull=False
        ).values_list("vaccine", flat=True)

        vaccines.update(subactivity_vaccines)
        return sorted(list(vaccines))

    @property
    def subactivities_single_vaccine_list(self):
        return sorted(list(Campaign.split_combined_vaccines(set(self.subactivities_vaccine_list))))

    @property
    def subactivities_vaccine_names(self):
        return ", ".join(self.subactivities_vaccine_list)

    @property
    def subactivities_single_vaccine_names(self):
        return ", ".join(self.subactivities_single_vaccine_list)

    @property
    def vaccine_list_extended(self):
        """list of vaccines including from sub-activities"""
        vaccines = set()
        vaccines.update(self.vaccine_list)
        vaccines.update(self.subactivities_vaccine_list)
        return sorted(list(vaccines))

    @property
    def single_vaccine_list_extended(self):
        return sorted(list(Campaign.split_combined_vaccines(set(self.vaccine_list_extended))))

    @property
    def vaccine_names_extended(self):
        return ", ".join(self.vaccine_list_extended)

    @property
    def single_vaccine_names_extended(self):
        return ", ".join(self.single_vaccine_list_extended)

    @property
    def districts_count_calculated(self):
        return len(self.campaign.get_districts_for_round(self))


class CampaignType(models.Model):
    POLIO = "Polio"
    MEASLES = "Measles"
    PIRI = "PIRI"
    YELLOW_FEVER = "Yellow fever"
    VITAMIN_A = "Vitamin A"
    RUBELLA = "Rubella"
    DEWORMING = "Deworming"
    # This is the types that we know at the moment.
    # Clients will have the possibility to add new types

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify_underscore(self.name)
        super(CampaignType, self).save(*args, **kwargs)


class CampaignQuerySet(models.QuerySet):
    def filter_for_user(self, user: Union[User, AnonymousUser]):
        qs = self
        if user.is_authenticated:
            # Authenticated users only get campaigns linked to their account
            qs = qs.filter(account=user.iaso_profile.account)

            # Restrict Campaign to the OrgUnit on the country he can access
            if user.iaso_profile.org_units.count() and not user.is_superuser:
                org_units = OrgUnit.objects.hierarchy(user.iaso_profile.org_units.all()).defer(
                    "geom", "simplified_geom"
                )
                qs = qs.filter(Q(country__in=org_units) | Q(initial_org_unit__in=org_units))
        return qs


class PolioCampaignManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().prefetch_related("campaign_types").filter(campaign_types__name=CampaignType.POLIO)


class Campaign(SoftDeletableModel):
    class Meta:
        ordering = ["obr_name"]

    # Managers.
    objects = models.Manager.from_queryset(CampaignQuerySet)()
    polio_objects = PolioCampaignManager.from_queryset(CampaignQuerySet)()

    scopes: "django.db.models.manager.RelatedManager[CampaignScope]"
    rounds: "django.db.models.manager.RelatedManager[Round]"
    id = models.UUIDField(default=uuid4, primary_key=True, editable=False)
    account = models.ForeignKey("iaso.account", on_delete=models.CASCADE, related_name="campaigns")
    epid = models.CharField(default=None, max_length=255, null=True, blank=True)
    obr_name = models.CharField(max_length=255, unique=True)
    is_preventive = models.BooleanField(default=False, help_text="Preventive campaign")
    # campaign used for training and testing purpose
    is_test = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    campaign_types = models.ManyToManyField(CampaignType, blank=True, related_name="campaigns")

    gpei_coordinator = models.CharField(max_length=255, null=True, blank=True)
    gpei_email = models.EmailField(max_length=254, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    separate_scopes_per_round = models.BooleanField(default=False)
    initial_org_unit = models.ForeignKey(
        "iaso.orgunit", null=True, blank=True, on_delete=models.SET_NULL, related_name="campaigns"
    )

    enable_send_weekly_email = models.BooleanField(
        default=False, help_text="Activate the sending of a reminder email every week."
    )

    country = models.ForeignKey(
        "iaso.orgunit",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="campaigns_country",
        help_text="Country for campaign, set automatically from initial_org_unit",
    )
    # We use a geojson and not a geom because we have a feature per vaccine x round (if separate scope per round)
    # It is a feature collection. Basic info about the campaign are in the properties
    geojson = models.JSONField(
        null=True,
        editable=False,
        blank=True,
        help_text="GeoJson representing the scope of the campaign",
        encoder=DjangoJSONEncoder,
    )

    creation_email_send_at = models.DateTimeField(
        null=True, blank=True, help_text="When and if we sent an email for creation"
    )

    # Campaign group.
    group = models.ForeignKey(
        Group,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="campaigns",
        default=None,
        limit_choices_to={"domain": "POLIO"},
    )

    onset_at = models.DateField(
        null=True,
        help_text=_("When the campaign starts"),
        blank=True,
    )

    outbreak_declaration_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Outbreak declaration date"),
    )

    # This is considered the "first" date.
    cvdpv2_notified_at = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("cVDPV2 Notification"),
    )

    pv_notified_at = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("PV Notification"),
    )

    pv2_notified_at = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("PV2 Notification"),
    )

    virus = models.CharField(max_length=15, choices=VIRUSES, null=True, blank=True)

    # Detection.
    detection_status = models.CharField(default="PENDING", max_length=10, choices=STATUS)
    detection_responsible = models.CharField(max_length=10, choices=RESPONSIBLES, null=True, blank=True)
    detection_first_draft_submitted_at = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("1st Draft Submission"),
    )

    # Risk Assessment.
    risk_assessment_status = models.CharField(max_length=10, choices=RA_BUDGET_STATUSES, null=True, blank=True)
    risk_assessment_responsible = models.CharField(max_length=10, choices=RESPONSIBLES, null=True, blank=True)
    investigation_at = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Field Investigation Date"),
    )
    risk_assessment_first_draft_submitted_at = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("1st Draft Submission"),
    )
    risk_assessment_rrt_oprtt_approval_at = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("RRT/OPRTT Approval"),
    )
    ag_nopv_group_met_at = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("AG/nOPV Group"),
    )
    dg_authorized_at = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("DG Authorization"),
    )
    verification_score = models.IntegerField(null=True, blank=True)
    # END OF Risk assessment field

    # Unusable vials leftover 14 days after the last round ends

    # ----------------------------------------------------------------------------------------
    # START fields moved to the `Budget` model. **********************************************
    budget_status = models.CharField(max_length=100, null=True, blank=True)
    budget_current_state_key = models.CharField(max_length=100, default="-")
    budget_current_state_label = models.CharField(max_length=100, null=True, blank=True)

    # Budget tab
    # These fields can be either filled manually or via the budget workflow when a step is done.
    ra_completed_at_WFEDITABLE = models.DateField(null=True, blank=True)
    who_sent_budget_at_WFEDITABLE = models.DateField(null=True, blank=True)
    unicef_sent_budget_at_WFEDITABLE = models.DateField(null=True, blank=True)
    gpei_consolidated_budgets_at_WFEDITABLE = models.DateField(null=True, blank=True)
    submitted_to_rrt_at_WFEDITABLE = models.DateField(null=True, blank=True)
    feedback_sent_to_gpei_at_WFEDITABLE = models.DateField(null=True, blank=True)
    re_submitted_to_rrt_at_WFEDITABLE = models.DateField(null=True, blank=True)
    submitted_to_orpg_operations1_at_WFEDITABLE = models.DateField(null=True, blank=True)
    feedback_sent_to_rrt1_at_WFEDITABLE = models.DateField(null=True, blank=True)
    re_submitted_to_orpg_operations1_at_WFEDITABLE = models.DateField(null=True, blank=True)
    submitted_to_orpg_wider_at_WFEDITABLE = models.DateField(null=True, blank=True)
    submitted_to_orpg_operations2_at_WFEDITABLE = models.DateField(null=True, blank=True)
    feedback_sent_to_rrt2_at_WFEDITABLE = models.DateField(null=True, blank=True)
    re_submitted_to_orpg_operations2_at_WFEDITABLE = models.DateField(null=True, blank=True)
    submitted_for_approval_at_WFEDITABLE = models.DateField(null=True, blank=True)
    feedback_sent_to_orpg_operations_unicef_at_WFEDITABLE = models.DateField(null=True, blank=True)
    feedback_sent_to_orpg_operations_who_at_WFEDITABLE = models.DateField(null=True, blank=True)
    approved_by_who_at_WFEDITABLE = models.DateField(null=True, blank=True)
    approved_by_unicef_at_WFEDITABLE = models.DateField(null=True, blank=True)
    approved_at_WFEDITABLE = models.DateField(null=True, blank=True)
    approval_confirmed_at_WFEDITABLE = models.DateField(null=True, blank=True)

    # Fund release part of the budget form. Will be migrated to workflow fields later.
    who_disbursed_to_co_at = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Disbursed to CO (WHO)"),
    )
    who_disbursed_to_moh_at = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Disbursed to MOH (WHO)"),
    )
    unicef_disbursed_to_co_at = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Disbursed to CO (UNICEF)"),
    )
    unicef_disbursed_to_moh_at = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Disbursed to MOH (UNICEF)"),
    )

    no_regret_fund_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    payment_mode = models.CharField(max_length=30, choices=PAYMENT, null=True, blank=True)
    district_count = models.IntegerField(null=True, blank=True)
    # END fields moved to the `Budget` model. ************************************************
    # ----------------------------------------------------------------------------------------

    def __str__(self):
        return f"{self.epid} {self.obr_name}"

    @property
    def has_polio_type(self) -> bool:
        return self.campaign_types.filter(name=CampaignType.POLIO).exists()

    def get_item_by_key(self, key):
        return getattr(self, key)

    def get_districts_for_round_number(self, round_number):
        if self.separate_scopes_per_round:
            return (
                OrgUnit.objects.filter(groups__roundScope__round__number=round_number)
                .filter(groups__roundScope__round__campaign=self)
                .distinct()
                .defer("geom", "simplified_geom")
            )
        return self.get_campaign_scope_districts_qs()

    def get_districts_for_round(self, round):
        districts = []
        if self.separate_scopes_per_round:
            id_set = set()
            for scope in round.scopes.all():
                for ou in scope.group.org_units.all():
                    if ou.id not in id_set:
                        id_set.add(ou.id)
                        districts.append(ou)
        else:
            districts = self.get_campaign_scope_districts()
        return districts

    def get_districts_for_round_qs(self, round):
        if self.separate_scopes_per_round:
            districts = (
                OrgUnit.objects.filter(groups__roundScope__round=round)
                .filter(validation_status="VALID")
                .distinct()
                .defer("geom", "simplified_geom")
            )
        else:
            districts = self.get_campaign_scope_districts_qs()
        return districts

    def get_campaign_scope_districts(self):
        # Get districts on campaign scope, make only sense if separate_scopes_per_round=True
        id_set = set()
        districts = []
        for scope in self.scopes.all():
            for ou in scope.group.org_units.all():
                if ou.id not in id_set:
                    id_set.add(ou.id)
                    districts.append(ou)

        return districts

    def get_campaign_scope_districts_qs(self):
        # Get districts on campaign scope, make only sense if separate_scopes_per_round=True
        return (
            OrgUnit.objects.filter(groups__campaignScope__campaign=self)
            .filter(validation_status="VALID")
            .defer("geom", "simplified_geom")
        )

    def get_all_districts(self):
        """District from all round merged as one"""
        if self.separate_scopes_per_round:
            return (
                OrgUnit.objects.filter(groups__roundScope__round__campaign=self)
                .filter(validation_status="VALID")
                .distinct()
                .defer("geom", "simplified_geom")
            )
        return self.get_campaign_scope_districts()

    def get_all_districts_qs(self):
        """District from all round merged as one"""
        if self.separate_scopes_per_round:
            return (
                OrgUnit.objects.filter(groups__roundScope__round__campaign=self)
                .filter(validation_status="VALID")
                .distinct()
                .defer("geom", "simplified_geom")
            )
        return self.get_campaign_scope_districts_qs()

    # Returning date.min if ended_at has no value so the method can be used with `sorted`
    def get_last_round_end_date(self):
        sorted_rounds = sorted(
            list(self.rounds.all()),
            key=lambda round: round.ended_at if round.ended_at else date.min,
            reverse=True,
        )
        return sorted_rounds[0].ended_at if sorted_rounds[0].ended_at else date.min

    def is_started(self, reference_date=None):
        if reference_date is None:
            reference_date = datetime.datetime.now()
        started_rounds = self.rounds.filter(started_at__lte=reference_date)
        return started_rounds.count() > 0

    def find_rounds_with_date(self, date_type="start", round_number=None):
        rounds = self.rounds.all()
        if round_number is not None:
            rounds = rounds.filter(number=round_number)
        if date_type == "start":
            return rounds.exclude(started_at=None).order_by("-started_at")
        if date_type == "end":
            return rounds.exclude(ended_at=None).order_by("-ended_at")

    def find_last_round_with_date(self, date_type="start", round_number=None):
        return self.find_rounds_with_date(date_type, round_number).first()

    def save(self, *args, **kwargs):
        if self.initial_org_unit is not None:
            try:
                country = self.initial_org_unit.ancestors().filter(org_unit_type__category="COUNTRY").first()
                self.country = country
            except OrgUnit.DoesNotExist:
                pass

        super().save(*args, **kwargs)

    @property
    def campaign_level_vaccines_list(self):
        """Vaccine types from campaign level scopes.
        Combined type nOPV2&bOPV2 is treated as separate from its components nOPV2 and bOPV2"""

        if self.separate_scopes_per_round:
            return []

        vaccines = set()

        campaign_vaccines = CampaignScope.objects.filter(
            campaign=self, group__org_units__isnull=False, vaccine__isnull=False
        ).values_list("vaccine", flat=True)

        vaccines.update(campaign_vaccines)
        return sorted(list(vaccines))

    @property
    def campaign_level_single_vaccines_list(self):
        """Same as self.campaign_level_vaccines_list, but the vaccine type nOPV2&bOPV2 is split.
        So a campaign with nOPV2 and nOPV2&bOPV2 in its scopes will only have 2 elements in the list.
        Useful when dealing with actual vaccines, eg: vaccine stocks

        """
        vaccines = set(self.campaign_level_vaccines_list)
        return sorted(list(self.split_combined_vaccines(vaccines)))

    @property
    def round_level_vaccines_list(self):
        """vaccines from round level scopes, excluding subactivities
        Combined type nOPV2&bOPV2 is treated as separate from its components nOPV2 and bOPV2"""
        if not self.separate_scopes_per_round:
            return []

        vaccines = set()
        rnds = self.rounds.all().values("id")

        round_vaccines = RoundScope.objects.filter(
            round__id__in=Subquery(rnds), group__org_units__isnull=False, vaccine__isnull=False
        ).values_list("vaccine", flat=True)

        vaccines.update(round_vaccines)
        return sorted(list(vaccines))

    @property
    def round_level_single_vaccines_list(self):
        """Same as self.round_level_vaccines_list, but the vaccine type nOPV2&bOPV2 is split.
        So a campaign with nOPV2 and nOPV2&bOPV2 in its scopes will only have 2 elements in the list.
        Useful when dealing with actual vaccines, eg: vaccine stocks
        """
        vaccines = set(self.round_level_vaccines_list)
        return sorted(list(self.split_combined_vaccines(vaccines)))

    @property
    def sub_activity_level_vaccines_list(self):
        """List of vaccines from sub-activities scopes (excluding parent round scopes)
        Combined type nOPV2&bOPV2 is treated as separate from its components nOPV2 and bOPV2"""
        vaccines = set()
        rnds = self.rounds.all().values("id")

        subactivity_vaccines = SubActivityScope.objects.filter(
            subactivity__round__id__in=Subquery(rnds), group__org_units__isnull=False, vaccine__isnull=False
        ).values_list("vaccine", flat=True)

        vaccines.update(subactivity_vaccines)
        return sorted(list(vaccines))

    @property
    def sub_activity_level_single_vaccines_list(self):
        """Same as self.sub_activity_level_vaccines_list, but the vaccine type nOPV2&bOPV2 is split.
        So a campaign with nOPV2 and nOPV2&bOPV2 in its scopes will only have 2 elements in the list.
        Useful when dealing with actual vaccines, eg: vaccine stocks

        """
        vaccines = set(self.sub_activity_level_vaccines_list)
        return sorted(list(self.split_combined_vaccines(vaccines)))

    @property
    def vaccines_extended_list(self):
        vaccines = set()
        vaccines.update(self.campaign_level_vaccines_list)
        vaccines.update(self.round_level_vaccines_list)
        return sorted(list(vaccines))

    @property
    def vaccines_full_list(self):
        vaccines = set()
        vaccines.update(self.campaign_level_vaccines_list)
        vaccines.update(self.round_level_vaccines_list)
        vaccines.update(self.sub_activity_level_vaccines_list)
        return sorted(list(vaccines))

    @property
    def single_vaccines_extended_list(self):
        """Same as self.vaccines_extended_list, but the vaccine type nOPV2&bOPV2 is split.
        So a campaign with nOPV2 and nOPV2&bOPV2 in its scopes will only have 2 elements in the list.
        Useful when dealing with actual vaccines, eg: vaccine stocks
        """
        vaccines = set(self.vaccines_extended_list)
        return sorted(list(self.split_combined_vaccines(vaccines)))

    @property
    def single_vaccines_full_list(self):
        """Same as self.single_vaccines_full_list, but includes sub_activities"""
        vaccines = set(self.vaccines_full_list)
        return sorted(list(self.split_combined_vaccines(vaccines)))

    # deprecated
    # equivalent to vaccines_extended
    # currently used in preparedness
    @property
    def vaccines(self):
        return ", ".join(self.vaccines_extended_list)

    @property
    def vaccines_extended(self):
        return ", ".join(self.vaccines_extended_list)

    @property
    def vaccines_full(self):
        return ", ".join(self.vaccines_full_list)

    @property
    def single_vaccines_extended(self):
        return ", ".join(self.single_vaccines_extended_list)

    @property
    def single_vaccines_full(self):
        return ", ".join(self.single_vaccines_full_list)

    @staticmethod
    def split_combined_vaccines(vaccines):
        if VACCINES[3][0] in vaccines:
            vaccines.remove(VACCINES[3][0])
            vaccines.add(VACCINES[1][0])
            vaccines.add(VACCINES[2][0])
        return vaccines

    def update_geojson_field(self):
        "Update the geojson field on the campaign DOES NOT TRIGGER the save() you have to do it manually"
        campaign = self
        features = []
        if not self.separate_scopes_per_round:
            campaign_scopes = self.scopes.all()

            # noinspection SqlResolve
            campaign_scopes = campaign_scopes.annotate(
                geom=RawSQL(
                    """SELECT st_asgeojson(st_simplify(st_union(st_buffer(iaso_orgunit.simplified_geom::geometry, 0)), 0.01)::geography)
    from iaso_orgunit right join iaso_group_org_units ON iaso_group_org_units.orgunit_id = iaso_orgunit.id
    where group_id = polio_campaignscope.group_id""",
                    [],
                )
            )

            for scope in campaign_scopes:
                if scope.geom:
                    feature = {
                        "type": "Feature",
                        "geometry": json.loads(scope.geom),
                        "properties": {
                            "obr_name": campaign.obr_name,
                            "id": str(campaign.id),
                            "vaccine": scope.vaccine if scope.vaccine else None,
                            "scope_key": f"campaignScope-{scope.id}",
                            "top_level_org_unit_name": scope.campaign.country.name,
                        },
                    }
                    features.append(feature)
        else:
            round_scopes = RoundScope.objects.filter(round__campaign=campaign).all()
            round_scopes = round_scopes.prefetch_related("round")
            # noinspection SqlResolve
            round_scopes = round_scopes.annotate(
                geom=RawSQL(
                    """select st_asgeojson(st_simplify(st_union(st_buffer(iaso_orgunit.simplified_geom::geometry, 0)), 0.01)::geography)
    from iaso_orgunit right join iaso_group_org_units ON iaso_group_org_units.orgunit_id = iaso_orgunit.id
    where group_id = polio_roundscope.group_id""",
                    [],
                )
            )

            for scope in round_scopes:
                if scope.geom:
                    feature = {
                        "type": "Feature",
                        "geometry": json.loads(scope.geom),
                        "properties": {
                            "obr_name": campaign.obr_name,
                            "id": str(campaign.id),
                            "vaccine": scope.vaccine if scope.vaccine else None,
                            "scope_key": f"roundScope-{scope.id}",
                            "top_level_org_unit_name": campaign.country.name,
                            "round_number": scope.round.number,
                        },
                    }
                    features.append(feature)

        self.geojson = features


# Deprecated
class Preparedness(models.Model):
    id = models.UUIDField(default=uuid4, primary_key=True, editable=False)
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE)
    spreadsheet_url = models.URLField()

    national_score = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("National Score"))
    regional_score = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Regional Score"))
    district_score = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("District Score"))

    payload = models.JSONField()

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self) -> str:
        return f"{self.campaign} - {self.created_at}"


class CountryUsersGroup(models.Model):
    users = models.ManyToManyField(User, blank=True)
    country = models.OneToOneField(OrgUnit, on_delete=models.CASCADE)
    language = models.CharField(max_length=32, choices=LANGUAGES, default="EN")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    # used for workflow
    teams = models.ManyToManyField(Team, help_text="Teams used by the country", blank=True)

    def __str__(self):
        return str(self.country)


class URLCache(models.Model):
    url = models.URLField(unique=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return self.url


class SpreadSheetImport(models.Model):
    """A copy of a Google Spreadsheet in the DB, in JSON format

    This allows us to separate the parsing of the datasheet from its retrieval
    and to keep a history.
    """

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    url = models.URLField()
    content = models.JSONField()
    spread_id = models.CharField(max_length=60, db_index=True)

    @staticmethod
    def create_for_url(spreadsheet_url: str):
        spread = open_sheet_by_url(spreadsheet_url)
        cached_spread = CachedSpread.from_spread(spread)
        return SpreadSheetImport.objects.create(content=cached_spread.c, url=spreadsheet_url, spread_id=spread.id)

    @property
    def cached_spreadsheet(self):
        return CachedSpread(self.content)

    @staticmethod
    def last_for_url(spreadsheet_url: str):
        if not spreadsheet_url:
            return None
        spread_id = extract_id_from_url(spreadsheet_url)

        ssis = SpreadSheetImport.objects.filter(spread_id=spread_id)

        if not ssis:
            # No import yet
            return None
        return ssis.latest("created_at")


class CampaignGroup(SoftDeletableModel):
    def __str__(self):
        return f"{self.name} {','.join(str(c) for c in self.campaigns.all())}"

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=200)
    campaigns = models.ManyToManyField(Campaign, related_name="grouped_campaigns")


# Deprecated
class BudgetEvent(SoftDeletableModel):
    TYPES = (
        ("submission", "Budget Submission"),
        ("comments", "Comments"),
        ("validation", "Approval"),
        ("request", "Request"),
        ("feedback", "Feedback"),
        ("review", "Review"),
        ("transmission", "Transmission"),
    )

    STATUS = (("validation_ongoing", "Validation Ongoing"), ("validated", "Validated"))

    campaign = models.ForeignKey(Campaign, on_delete=models.PROTECT, related_name="budget_events")
    type = models.CharField(choices=TYPES, max_length=200)
    author = models.ForeignKey(User, blank=False, null=False, on_delete=models.PROTECT)
    internal = models.BooleanField(default=False)
    target_teams = models.ManyToManyField(Team)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(choices=STATUS, max_length=200, null=True, default="validation_ongoing")
    cc_emails = models.CharField(max_length=200, blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    links = models.TextField(blank=True, null=True)
    is_finalized = models.BooleanField(default=False)
    is_email_sent = models.BooleanField(default=False)
    amount = models.DecimalField(blank=True, null=True, decimal_places=2, max_digits=14)

    def __str__(self):
        return str(self.campaign)


# Deprecated
class BudgetFiles(models.Model):
    event = models.ForeignKey(BudgetEvent, on_delete=models.PROTECT, related_name="event_files")
    file = models.FileField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Budget File"
        verbose_name_plural = "Budget Files"

    def __str__(self):
        return str(self.event)


class VaccineAuthorizationStatus(models.TextChoices):
    PENDING = "ONGOING", _("Ongoing")
    VALIDATED = "VALIDATED", _("Validated")
    IGNORED = "SIGNATURE", _("Sent for signature")
    EXPIRED = "EXPIRED", _("Expired")


class VaccineAuthorization(SoftDeletableModel):
    country = models.ForeignKey(
        "iaso.orgunit", null=True, blank=True, on_delete=models.SET_NULL, related_name="vaccineauthorization"
    )
    account = models.ForeignKey("iaso.account", on_delete=models.DO_NOTHING, related_name="vaccineauthorization")
    start_date = models.DateField(blank=True, null=True)
    expiration_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    quantity = models.IntegerField(blank=True, null=True)
    status = models.CharField(null=True, blank=True, choices=VaccineAuthorizationStatus.choices, max_length=200)
    comment = models.TextField(max_length=250, blank=True, null=True)

    def __str__(self):
        return f"{self.country}-{self.expiration_date}"


class NotificationManager(models.Manager):
    def get_countries_for_account(self, account: Account) -> QuerySet[OrgUnit]:
        """
        Returns a queryset of unique countries used in notifications for the given account.
        """
        countries_pk = self.filter(account=account, org_unit__version_id=account.default_version_id).values_list(
            "org_unit__parent__parent__id", flat=True
        )
        return OrgUnit.objects.filter(pk__in=countries_pk).defer("geom", "simplified_geom").order_by("name")


class CustomPublicStorage(
    S3Boto3Storage if os.environ.get("AWS_PUBLIC_STORAGE_BUCKET_NAME") else import_string(settings.DEFAULT_FILE_STORAGE)
):
    if os.environ.get("AWS_PUBLIC_STORAGE_BUCKET_NAME"):
        default_acl = "public-read"
        file_overwrite = False
        querystring_auth = False
        bucket_name = os.environ.get("AWS_PUBLIC_STORAGE_BUCKET_NAME", "")


## Terminology
# VRF = Vaccine Request Form
# VPA = Vaccine Pre Alert
# VAR = Vaccine Arrival Report


class VaccineRequestFormType(models.TextChoices):
    NORMAL = "Normal", _("Normal")
    MISSING = "Missing", _("Missing")
    NOT_REQUIRED = "Not Required", _("Not Required")


class VaccineRequestForm(SoftDeletableModel):
    class Meta:
        indexes = [
            models.Index(fields=["campaign", "vaccine_type"]),  # Frequently filtered together
            models.Index(fields=["vrf_type"]),  # Filtered in repository_forms.py
            models.Index(fields=["created_at"]),  # Used for ordering
            models.Index(fields=["updated_at"]),  # Used for ordering
        ]

    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, db_index=True)
    vaccine_type = models.CharField(max_length=30, choices=INDIVIDUAL_VACCINES)
    rounds = models.ManyToManyField(Round, db_index=True)
    date_vrf_signature = models.DateField(null=True, blank=True)
    date_vrf_reception = models.DateField(null=True, blank=True)
    date_dg_approval = models.DateField(null=True, blank=True)
    quantities_ordered_in_doses = models.PositiveIntegerField(null=True, blank=True, default=0)
    vrf_type = models.CharField(
        max_length=20, choices=VaccineRequestFormType.choices, default=VaccineRequestFormType.NORMAL
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # optional fields
    wastage_rate_used_on_vrf = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    date_vrf_submission_to_orpg = models.DateField(null=True, blank=True)
    quantities_approved_by_orpg_in_doses = models.PositiveIntegerField(null=True, blank=True)
    date_rrt_orpg_approval = models.DateField(null=True, blank=True)
    date_vrf_submitted_to_dg = models.DateField(null=True, blank=True)
    quantities_approved_by_dg_in_doses = models.PositiveIntegerField(null=True, blank=True)
    comment = models.TextField(blank=True, null=True)
    target_population = models.PositiveIntegerField(null=True, blank=True)

    document = models.FileField(storage=CustomPublicStorage(), upload_to="public_documents/vrf/", null=True, blank=True)

    objects = DefaultSoftDeletableManager()

    def get_country(self):
        return self.campaign.country

    def count_pre_alerts(self):
        return self.vaccineprealert_set.count()

    def count_arrival_reports(self):
        return self.vaccinearrivalreport_set.count()

    def total_doses_shipped(self):
        return self.vaccineprealert_set.all().aggregate(total_doses_shipped=Coalesce(Sum("doses_shipped"), 0))[
            "total_doses_shipped"
        ]

    def total_doses_received(self):
        return self.vaccinearrivalreport_set.all().aggregate(total_doses_received=Coalesce(Sum("doses_received"), 0))[
            "total_doses_received"
        ]

    def __str__(self):
        return f"VRF for {self.get_country()} {self.campaign} {self.vaccine_type} #VPA {self.count_pre_alerts()} #VAR {self.count_arrival_reports()}"


class VaccinePreAlert(models.Model):
    request_form = models.ForeignKey(VaccineRequestForm, on_delete=models.CASCADE)
    date_pre_alert_reception = models.DateField()
    po_number = models.CharField(max_length=200, blank=True, null=True, default=None, unique=True)
    estimated_arrival_time = models.DateField(blank=True, null=True, default=None)
    lot_numbers = ArrayField(models.CharField(max_length=200, blank=True), default=list)
    expiration_date = models.DateField(blank=True, null=True, default=None)
    doses_shipped = models.PositiveIntegerField(blank=True, null=True, default=None)
    doses_per_vial = models.PositiveIntegerField(blank=True, null=True, default=None)
    vials_shipped = models.PositiveIntegerField(blank=True, null=True, default=None)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    document = models.FileField(
        storage=CustomPublicStorage(), upload_to="public_documents/prealert/", null=True, blank=True
    )

    def save(self, *args, **kwargs):
        self.doses_per_vial = self.get_doses_per_vial()

        if self.doses_shipped is None:
            self.vials_shipped = None
        else:
            self.vials_shipped = math.ceil(self.doses_shipped / self.doses_per_vial)

        super().save(*args, **kwargs)

    def get_doses_per_vial(self):
        return DOSES_PER_VIAL[self.request_form.vaccine_type]

    class Meta:
        indexes = [
            models.Index(fields=["request_form", "estimated_arrival_time"]),  # Used together in queries
            models.Index(fields=["po_number"]),  # Unique field that's queried
            models.Index(fields=["date_pre_alert_reception"]),  # Used for filtering/ordering
        ]


class VaccineArrivalReport(models.Model):
    request_form = models.ForeignKey(VaccineRequestForm, on_delete=models.CASCADE)
    arrival_report_date = models.DateField()
    doses_received = models.PositiveIntegerField()
    po_number = models.CharField(max_length=200, blank=True, null=True, default=None, unique=True)
    lot_numbers = ArrayField(models.CharField(max_length=200, blank=True), default=list)
    expiration_date = models.DateField(blank=True, null=True, default=None)
    doses_shipped = models.PositiveIntegerField(blank=True, null=True, default=None)
    doses_per_vial = models.PositiveIntegerField(blank=True, null=True, default=None)
    vials_shipped = models.PositiveIntegerField(blank=True, null=True, default=None)
    vials_received = models.PositiveIntegerField(blank=True, null=True, default=None)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_doses_per_vial(self):
        return DOSES_PER_VIAL[self.request_form.vaccine_type]

    def save(self, *args, **kwargs):
        # We overwrite these values because they are not editable by the user
        self.doses_per_vial = self.get_doses_per_vial()

        if self.doses_shipped is None:
            self.vials_shipped = None
        else:
            self.vials_shipped = math.ceil(self.doses_shipped / self.doses_per_vial)

        if self.doses_received is None:
            self.vials_received = None
        else:
            self.vials_received = math.ceil(self.doses_received / self.doses_per_vial)

        super().save(*args, **kwargs)

    class Meta:
        indexes = [
            models.Index(fields=["request_form", "arrival_report_date"]),  # Frequently queried together
            models.Index(fields=["po_number"]),  # Unique field that's queried
            models.Index(fields=["doses_received"]),  # Used in aggregations
        ]


class VaccineStock(models.Model):
    account = models.ForeignKey("iaso.account", on_delete=models.CASCADE, related_name="vaccine_stocks")
    country = models.ForeignKey(
        "iaso.orgunit",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="vaccine_stocks",
        help_text="Unique (Country, Vaccine) pair",
    )
    vaccine = models.CharField(max_length=12, choices=VACCINES)

    class Meta:
        unique_together = ("country", "vaccine")
        indexes = [
            models.Index(fields=["country", "vaccine"]),  # Already unique_together, but used in many queries
            models.Index(fields=["account"]),  # Frequently filtered by account
        ]

    def __str__(self):
        return f"{self.country} - {self.vaccine}"


class VaccineStockHistoryQuerySet(models.QuerySet):
    def filter_for_user(self, user: Optional[Union[User, AnonymousUser]]):
        if not user or not user.is_authenticated:
            raise UserNotAuthError(f"User not Authenticated")

        profile = user.iaso_profile
        self = self.filter(vaccine_stock__account=profile.account)

        return self


class VaccineStockHistory(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    vaccine_stock = models.ForeignKey(VaccineStock, on_delete=models.CASCADE, related_name="history")
    round = models.ForeignKey(Round, on_delete=models.CASCADE, related_name="stock_on_closing")
    unusable_vials_in = models.IntegerField(null=True)
    unusable_vials_out = models.IntegerField(null=True)
    unusable_doses_in = models.IntegerField(null=True)
    unusable_doses_out = models.IntegerField(null=True)
    usable_vials_in = models.IntegerField(null=True)
    usable_vials_out = models.IntegerField(null=True)
    usable_doses_in = models.IntegerField(null=True)
    usable_doses_out = models.IntegerField(null=True)

    objects = models.Manager.from_queryset(VaccineStockHistoryQuerySet)()

    class Meta:
        unique_together = ("round", "vaccine_stock")


# Form A
class OutgoingStockMovement(models.Model):
    class Meta:
        indexes = [
            models.Index(fields=["vaccine_stock", "campaign"]),  # Frequently queried together
            models.Index(fields=["form_a_reception_date"]),  # Used in ordering
            models.Index(fields=["report_date"]),  # Used in filtering/ordering
        ]

    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE)
    round = models.ForeignKey(Round, on_delete=models.CASCADE, null=True, blank=True)
    vaccine_stock = models.ForeignKey(
        VaccineStock, on_delete=models.CASCADE
    )  # Country can be deduced from the campaign
    report_date = models.DateField()
    form_a_reception_date = models.DateField()
    usable_vials_used = models.PositiveIntegerField()
    lot_numbers = ArrayField(models.CharField(max_length=200, blank=True), default=list)
    missing_vials = models.PositiveIntegerField()
    comment = models.TextField(blank=True, null=True)

    document = models.FileField(
        storage=CustomPublicStorage(), upload_to="public_documents/forma/", null=True, blank=True
    )


class DestructionReport(models.Model):
    vaccine_stock = models.ForeignKey(VaccineStock, on_delete=models.CASCADE)
    action = models.TextField()
    rrt_destruction_report_reception_date = models.DateField()
    destruction_report_date = models.DateField()
    unusable_vials_destroyed = models.PositiveIntegerField()
    lot_numbers = ArrayField(models.CharField(max_length=200, blank=True), default=list)
    comment = models.TextField(blank=True, null=True)

    document = models.FileField(
        storage=CustomPublicStorage(), upload_to="public_documents/destructionreport/", null=True, blank=True
    )

    class Meta:
        indexes = [
            models.Index(fields=["vaccine_stock", "destruction_report_date"]),  # Used together in queries
            models.Index(fields=["rrt_destruction_report_reception_date"]),  # Used in filtering
        ]


class IncidentReport(models.Model):
    class StockCorrectionChoices(models.TextChoices):
        VVM_REACHED_DISCARD_POINT = "vvm_reached_discard_point", _("VVM reached the discard point")
        VACCINE_EXPIRED = "vaccine_expired", _("Vaccine expired")
        LOSSES = "losses", _("Losses")
        RETURN = "return", _("Return")
        STEALING = "stealing", _("Stealing")
        PHYSICAL_INVENTORY_ADD = "physical_inventory_add", _("Add to Physical Inventory")
        PHYSICAL_INVENTORY_REMOVE = "physical_inventory_remove", _("remove from Physical Inventory")
        BROKEN = "broken", _("Broken")
        UNREADABLE_LABEL = "unreadable_label", _("Unreadable label")

    vaccine_stock = models.ForeignKey(VaccineStock, on_delete=models.CASCADE)

    stock_correction = models.CharField(
        max_length=50, choices=StockCorrectionChoices.choices, default=StockCorrectionChoices.VVM_REACHED_DISCARD_POINT
    )
    title = models.CharField(max_length=255, null=True)
    comment = models.TextField(blank=True, null=True)
    date_of_incident_report = models.DateField()  # Date du document
    incident_report_received_by_rrt = models.DateField()  # Date reception document
    unusable_vials = models.PositiveIntegerField()
    usable_vials = models.PositiveIntegerField()

    document = models.FileField(
        storage=CustomPublicStorage(), upload_to="public_documents/incidentreport/", null=True, blank=True
    )

    class Meta:
        indexes = [
            models.Index(fields=["vaccine_stock", "date_of_incident_report"]),  # Frequently queried together
            models.Index(fields=["incident_report_received_by_rrt"]),  # Used in filtering
        ]


class EarmarkedStock(models.Model):
    class EarmarkedStockChoices(models.TextChoices):
        CREATED = "created", _("Created")  #     1. Usable -> Earmark
        USED = "used", _("Used")  #     2. Earmarked -> Used
        RETURNED = "returned", _("Returned")  #     3. Earmark -> Usable

    earmarked_stock_type = models.CharField(
        max_length=20, choices=EarmarkedStockChoices.choices, default=EarmarkedStockChoices.CREATED
    )
    vaccine_stock = models.ForeignKey(VaccineStock, on_delete=models.CASCADE, related_name="earmarked_stocks")
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE)
    round = models.ForeignKey(Round, on_delete=models.CASCADE)
    form_a = models.ForeignKey(
        OutgoingStockMovement, on_delete=models.CASCADE, null=True, blank=True, related_name="earmarked_stocks"
    )

    vials_earmarked = models.PositiveIntegerField()
    doses_earmarked = models.PositiveIntegerField()

    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["vaccine_stock", "campaign"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["round"]),
        ]

    def __str__(self):
        return f"Earmarked {self.vials_earmarked} vials for {self.campaign.obr_name} Round {self.round.number}"

    @classmethod
    def get_available_vials_count(cls, vaccine_stock: VaccineStock, _round: Round):
        matching_earmarks_plus = EarmarkedStock.objects.filter(
            vaccine_stock=vaccine_stock,
            campaign=_round.campaign,
            round=_round,
            earmarked_stock_type=EarmarkedStock.EarmarkedStockChoices.CREATED,
        )

        matching_earmarks_minus = EarmarkedStock.objects.filter(
            vaccine_stock=vaccine_stock,
            campaign=_round.campaign,
            round=_round,
            earmarked_stock_type__in=[
                EarmarkedStock.EarmarkedStockChoices.USED,
                EarmarkedStock.EarmarkedStockChoices.RETURNED,
            ],
        )

        total_vials_usable_plus = matching_earmarks_plus.aggregate(total=Sum("vials_earmarked"))["total"] or 0
        total_vials_usable_minus = matching_earmarks_minus.aggregate(total=Sum("vials_earmarked"))["total"] or 0

        total_vials_usable = total_vials_usable_plus - total_vials_usable_minus

        return total_vials_usable


class Notification(models.Model):
    """
    List of notifications of polio virus outbreaks.
    I.e. we found a case in this place on this day.

    Also called "line list": a table that summarizes key
    information about each case in an outbreak.

    Notifications can also be imported in bulk (see NotificationImport).
    """

    class VdpvCategories(models.TextChoices):
        """
        Vaccine-Derived PolioVirus categories.
        """

        AVDPV = "avdpv", _("aVDPV")
        CVDPV1 = "cvdpv1", _("cVDPV1")
        CVDPV2 = "cvdpv2", _("cVDPV2")
        NOPV2 = "nopv2", _("nOPV2")
        SABIN = "sabin", _("Sabin")
        SABIN1 = "sabin1", _("SABIN 1")
        SABIN2 = "sabin2", _("SABIN 2")
        SABIN3 = "sabin3", _("SABIN 3")
        VDPV = "vdpv", _("VDPV")
        VDPV1 = "vdpv1", _("VDPV1")
        VDPV2 = "vdpv2", _("VDPV2")
        VDPV3 = "vdpv3", _("VDPV3")
        VPV2 = "vpv2", _("VPV2")
        WPV1 = "wpv1", _("WPV1")

    class Sources(models.TextChoices):
        AFP = "accute_flaccid_paralysis", _(
            "Accute Flaccid Paralysis"
        )  # A case of someone who got paralyzed because of polio.
        CC = "contact_case", _("Contact Case")
        COMMUNITY = "community", _("Community")
        CONTACT = "contact", _("Contact")
        ENV = "environmental", _("Environmental")  # They found a virus in the environment.
        HC = "healthy_children", _("Healthy Children")
        OTHER = "other", _("Other")

    account = models.ForeignKey("iaso.account", on_delete=models.CASCADE)
    # EPID number = epidemiological number = unique identifier of a case per disease.
    epid_number = models.CharField(max_length=50, unique=True)
    vdpv_category = models.CharField(max_length=20, choices=VdpvCategories.choices, default=VdpvCategories.AVDPV)
    source = models.CharField(max_length=50, choices=Sources.choices, default=Sources.AFP)
    vdpv_nucleotide_diff_sabin2 = models.CharField(max_length=10, blank=True)
    # Lineage possible values: NIE-ZAS-1, RDC-MAN-3, Ambiguous, etc.
    lineage = models.CharField(max_length=150, blank=True)
    closest_match_vdpv2 = models.CharField(max_length=150, blank=True)
    date_of_onset = models.DateField(null=True, blank=True)
    date_results_received = models.DateField(null=True, blank=True)

    # Country / province / district are modelized as a hierarchy of OrgUnits.
    org_unit = models.ForeignKey(
        "iaso.orgunit", null=True, blank=True, on_delete=models.SET_NULL, related_name="polio_notifications"
    )
    site_name = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="polio_notification_created_set"
    )
    updated_at = models.DateTimeField(blank=True, null=True)
    updated_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="polio_notification_updated_set"
    )

    # `import_*` fields are populated when the data come from an .xlsx file.
    import_source = models.ForeignKey("NotificationImport", null=True, blank=True, on_delete=models.SET_NULL)
    import_raw_data = models.JSONField(null=True, blank=True, encoder=DjangoJSONEncoder)

    objects = NotificationManager()

    class Meta:
        verbose_name = _("Notification")

    def __str__(self) -> str:
        return f"{self.epid_number}"


class NotificationImport(models.Model):
    """
    Handle bulk import of polio virus outbreaks notifications via .xlsx files.
    This model stores .xlsx files and use them to populate `Notification`.
    """

    XLSX_TEMPLATE_PATH = "plugins/polio/fixtures/notifications_template.xlsx"

    EXPECTED_XLSX_COL_NAMES = [
        "EPID_NUMBER",
        "VDPV_CATEGORY",
        "SOURCE(AFP/ENV/CONTACT/HC)",
        "VDPV_NUCLEOTIDE_DIFF_SABIN2",
        "COUNTRY",
        "PROVINCE",
        "DISTRICT",
        "SITE_NAME/GEOCODE",
        "DATE_COLLECTION/DATE_OF_ONSET_(M/D/YYYY)",
        "LINEAGE",
        "CLOSEST_MATCH_VDPV2",
        "DATE_RESULTS_RECEIVED",
    ]

    class Status(models.TextChoices):
        NEW = "new", _("New")
        PENDING = "pending", _("Pending")
        DONE = "done", _("Done")

    account = models.ForeignKey("iaso.account", on_delete=models.CASCADE)
    file = models.FileField(upload_to="uploads/polio_notifications/%Y-%m-%d-%H-%M/")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.NEW)
    errors = models.JSONField(null=True, blank=True, encoder=DjangoJSONEncoder)
    created_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="polio_notification_import_created_set"
    )
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = _("Notification import")

    def __str__(self) -> str:
        return f"{self.file.name} - {self.status}"

    @classmethod
    def read_excel(cls, file: File) -> pd.DataFrame:
        try:
            df = pd.read_excel(file, keep_default_na=False)
        except Exception as err:
            raise ValueError(f"Invalid Excel file {file}.")

        # Normalize xlsx header's names.
        df.rename(columns=lambda name: name.upper().strip().replace(" ", "_"), inplace=True)
        for name in cls.EXPECTED_XLSX_COL_NAMES:
            if name not in df.columns:
                raise ValueError(f"Missing column {name}.")

        return df

    def create_notifications(self, created_by: User) -> None:
        """
        Can be launched async, see `create_polio_notifications_async`.
        """
        df = self.read_excel(self.file)
        self.status = self.Status.PENDING
        self.save()

        errors = []
        importer = NotificationXlsxImporter(
            org_units=OrgUnit.objects.filter(version_id=self.account.default_version_id).defer(
                "geom", "simplified_geom"
            )
        )

        for idx, row in df.iterrows():
            # Remove columns not in `EXPECTED_XLSX_COL_NAMES`.
            row_data_as_dict = {k: v for k, v in row.to_dict().items() if k in self.EXPECTED_XLSX_COL_NAMES}
            try:
                epid_number = importer.clean_str(row["EPID_NUMBER"])
                org_unit = importer.find_org_unit_in_caches(
                    country_name=importer.clean_str(row["COUNTRY"]),
                    region_name=importer.clean_str(row["PROVINCE"]),
                    district_name=importer.clean_str(row["DISTRICT"]),
                )
                defaults = {
                    "account": self.account,
                    "closest_match_vdpv2": importer.clean_str(row["CLOSEST_MATCH_VDPV2"]),
                    "date_of_onset": importer.clean_date(row["DATE_COLLECTION/DATE_OF_ONSET_(M/D/YYYY)"]),
                    "date_results_received": importer.clean_date(row["DATE_RESULTS_RECEIVED"]),
                    "import_raw_data": row_data_as_dict,
                    "import_source": self,
                    "lineage": importer.clean_str(row["LINEAGE"]),
                    "org_unit": org_unit,
                    "site_name": importer.clean_str(row["SITE_NAME/GEOCODE"]),
                    "source": importer.clean_source(row["SOURCE(AFP/ENV/CONTACT/HC)"]),
                    "vdpv_category": importer.clean_vdpv_category(row["VDPV_CATEGORY"]),
                    "vdpv_nucleotide_diff_sabin2": importer.clean_str(row["VDPV_NUCLEOTIDE_DIFF_SABIN2"]),
                }
                notification = Notification.objects.filter(epid_number=epid_number).first()
                if not notification:
                    notification = Notification(**defaults)
                    notification.epid_number = epid_number
                    notification.created_by = created_by
                    notification.save()
                else:
                    # If there is an import with an existing EPID, then we take the data
                    # as an update of the existing one.
                    for key, value in defaults.items():
                        setattr(notification, key, value)
                    notification.updated_by = created_by
                    notification.updated_at = timezone.now()
                    notification.save()
            except Exception:
                errors.append(row_data_as_dict)

        self.status = self.Status.DONE
        self.errors = errors
        self.updated_at = timezone.now()
        self.save()


@task_decorator(task_name="create_polio_notifications_async")
def create_polio_notifications_async(pk: int, task: Task = None) -> None:
    task.report_progress_and_stop_if_killed(progress_message="Importing polio notifications…")
    user = task.launcher
    notification_import = NotificationImport.objects.get(pk=pk)
    notification_import.create_notifications(created_by=user)
    num_created = Notification.objects.filter(import_source=notification_import).count()
    task.report_success(message=f"{num_created} polio notifications created.")


class NotificationXlsxImporter:
    def __init__(self, org_units: QuerySet[OrgUnit]):
        self.org_units = org_units
        self.countries_cache = None
        self.regions_cache = None
        self.districts_cache = None

    def build_org_unit_caches(self) -> Tuple[defaultdict, defaultdict, defaultdict]:
        from plugins.polio.api.common import make_orgunits_cache

        districts = (
            self.org_units.filter(org_unit_type__category="DISTRICT", validation_status=OrgUnit.VALIDATION_VALID)
            .defer("geom", "simplified_geom")
            .select_related("org_unit_type")
        )

        regions = (
            self.org_units.filter(
                OrgUnit.objects.parents_q(districts),
                org_unit_type__category="REGION",
                validation_status=OrgUnit.VALIDATION_VALID,
                path__depth=2,
            )
            .defer("geom", "simplified_geom")
            .select_related("org_unit_type")
        )

        countries = (
            self.org_units.filter(
                OrgUnit.objects.parents_q(districts),
                org_unit_type__category="COUNTRY",
                validation_status=OrgUnit.VALIDATION_VALID,
                path__depth=1,
            )
            .defer("geom", "simplified_geom")
            .select_related("org_unit_type")
        )

        districts_cache = make_orgunits_cache(districts)
        regions_cache = make_orgunits_cache(regions)
        countries_cache = make_orgunits_cache(countries)

        return countries_cache, regions_cache, districts_cache

    def find_org_unit_in_caches(self, country_name: str, region_name: str, district_name: str) -> Union[None, OrgUnit]:
        from plugins.polio.api.common import find_orgunit_in_cache

        if not self.countries_cache:
            self.countries_cache, self.regions_cache, self.districts_cache = self.build_org_unit_caches()

        country = find_orgunit_in_cache(self.countries_cache, country_name)
        region = None
        if country:
            region = find_orgunit_in_cache(self.regions_cache, region_name, country.name)
        if region:
            return find_orgunit_in_cache(self.districts_cache, district_name, region.name)
        return None

    def clean_str(self, data: Any) -> str:
        return str(data).strip()

    def clean_date(self, data: Any) -> Union[None, datetime.date]:
        try:
            return data.date()
        except AttributeError:
            return None

    def clean_vdpv_category(self, vdpv_category: str) -> Notification.VdpvCategories:
        vdpv_category = self.clean_str(vdpv_category).upper()
        vdpv_category = "".join(char for char in vdpv_category if char.isalnum())
        return Notification.VdpvCategories[vdpv_category]

    def clean_source(self, source: str) -> Notification.Sources:
        source = self.clean_str(source)
        try:
            # Find member by value.
            return Notification.Sources[source.upper()]
        except KeyError:
            pass
        try:
            # Find member by name.
            return Notification.Sources(source.lower().replace(" ", "_"))
        except Exception:
            pass
        if source.upper().startswith("CONT"):
            return Notification.Sources["CONTACT"]
        return Notification.Sources["OTHER"]
