import operator
import random
import re
import time
import typing
from functools import reduce
from io import StringIO
from logging import getLogger
from urllib.error import HTTPError
from urllib.request import urlopen

import django_cte
from bs4 import BeautifulSoup as Soup  # type: ignore
from django import forms as dj_forms
from django.contrib import auth
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.gis.db.models.fields import PointField
from django.contrib.gis.geos import Point
from django.contrib.postgres.aggregates import ArrayAgg
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.paginator import Paginator
from django.core.validators import MinLengthValidator
from django.db import models
from django.db.models import Count, Exists, FilteredRelation, OuterRef, Q
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField
from phonenumbers.phonenumberutil import region_code_for_number

from hat.menupermissions.constants import MODULES
from iaso.models.data_source import DataSource, SourceVersion
from iaso.models.org_unit import OrgUnit, OrgUnitReferenceInstance
from iaso.utils import extract_form_version_id, flat_parse_xml_soup
from iaso.utils.file_utils import get_file_type

from .. import periods
from ..utils.emoji import fix_emoji
from ..utils.jsonlogic import jsonlogic_to_q
from .device import Device, DeviceOwnership
from .forms import Form, FormVersion
from .project import Project

logger = getLogger(__name__)


# For compat
QUARTER = periods.PERIOD_TYPE_QUARTER
MONTH = periods.PERIOD_TYPE_MONTH
SIX_MONTH = periods.PERIOD_TYPE_SIX_MONTH


AGGREGATE = "AGGREGATE"
EVENT = "EVENT"
DERIVED = "DERIVED"
EVENT_TRACKER = "EVENT_TRACKER"

MAPPING_TYPE_CHOICES = (
    (AGGREGATE, _("Aggregate")),
    (EVENT, _("Event")),
    (EVENT_TRACKER, _("Event Tracker")),
    (DERIVED, _("Derived")),
)

QUEUED = "QUEUED"
RUNNING = "RUNNING"
ERRORED = "ERRORED"
EXPORTED = "EXPORTED"
SUCCESS = "SUCCESS"
SKIPPED = "SKIPPED"
KILLED = "KILLED"

STATUS_TYPE_CHOICES = (
    (QUEUED, _("Queued")),
    (RUNNING, _("Running")),
    (EXPORTED, _("Exported")),
    (ERRORED, _("Errored")),
    (SKIPPED, _("Skipped")),
    (KILLED, _("Killed")),
    (SUCCESS, _("Success")),
)
ALIVE_STATUSES = [QUEUED, RUNNING]


class KilledException(Exception):
    pass


def generate_id_for_dhis_2():
    letters = "abcdefghijklmnopqrstuvwxyz"
    letters = letters + letters.upper()
    all_chars = "0123456789" + letters
    first_letter = random.choice(letters)
    other_letters = random.choices(all_chars, k=10)
    return first_letter + "".join(other_letters)


class AccountFeatureFlag(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=255, primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.code})"


class ChoiceArrayField(ArrayField):
    """
    A field that allows us to store an array of choices.
    Uses Django's Postgres ArrayField
    and a MultipleChoiceField for its formfield.
    """

    def formfield(self, **kwargs):
        defaults = {
            "form_class": dj_forms.MultipleChoiceField,
            "choices": self.base_field.choices,
        }
        defaults.update(kwargs)
        # Skip our parent's formfield implementation completely as we don't
        # care for it.
        # pylint:disable=bad-super-call
        return super(ArrayField, self).formfield(**defaults)


MODULE_CHOICES = ((modu["codename"], modu["name"]) for modu in MODULES)


class Account(models.Model):
    """Account represent a tenant (=roughly a client organisation or a country)"""

    name = models.TextField(unique=True, validators=[MinLengthValidator(1)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    default_version = models.ForeignKey("SourceVersion", null=True, blank=True, on_delete=models.SET_NULL)
    feature_flags = models.ManyToManyField(AccountFeatureFlag)
    user_manual_path = models.TextField(null=True, blank=True)
    modules = ChoiceArrayField(
        models.CharField(max_length=100, choices=MODULE_CHOICES), blank=True, null=True, default=list
    )
    analytics_script = models.TextField(blank=True, null=True)

    def as_dict(self):
        return {
            "name": self.name,
            "id": self.id,
            "created_at": self.created_at.timestamp() if self.created_at else None,
            "updated_at": self.updated_at.timestamp() if self.updated_at else None,
            "default_version": self.default_version.as_dict() if self.default_version else None,
            "feature_flags": [flag.code for flag in self.feature_flags.all()],
            "user_manual_path": self.user_manual_path,
            "analytics_script": self.analytics_script,
        }

    def as_small_dict(self):
        return {
            "name": self.name,
            "id": self.id,
            "created_at": self.created_at.timestamp() if self.created_at else None,
            "updated_at": self.updated_at.timestamp() if self.updated_at else None,
            "default_version": self.default_version.as_small_dict() if self.default_version else None,
            "feature_flags": [flag.code for flag in self.feature_flags.all()],
            "user_manual_path": self.user_manual_path,
            "analytics_script": self.analytics_script,
        }

    def __str__(self):
        return "{} ".format(self.name)


class RecordType(models.Model):
    projects = models.ManyToManyField("Project", related_name="record_types", blank=True)
    name = models.TextField()
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class Record(models.Model):
    value = models.DecimalField(max_digits=19, decimal_places=10)
    version = models.ForeignKey(SourceVersion, null=True, blank=True, on_delete=models.CASCADE)
    org_unit = models.ForeignKey("OrgUnit", null=True, blank=True, on_delete=models.CASCADE)
    record_type = models.ForeignKey(RecordType, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class MatchingAlgorithm(models.Model):
    name = models.TextField()
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    projects = models.ManyToManyField("Project", related_name="match_algos", blank=True)

    def __str__(self):
        return "{} - {} {}".format(
            self.name,
            self.description,
            self.created_at.timestamp() if self.created_at else None,
        )

    def as_dict(self):
        return {"name": self.name, "id": self.id, "description": self.description}


class AlgorithmRun(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    algorithm = models.ForeignKey(MatchingAlgorithm, on_delete=models.CASCADE)
    launcher = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    result = models.JSONField(null=True, blank=True)
    finished = models.BooleanField(default=False)
    version_1 = models.ForeignKey(
        SourceVersion,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="runs_where_destination",
    )
    version_2 = models.ForeignKey(
        SourceVersion,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="runs_where_source",
    )

    def __str__(self):
        return "{} - {} - {}".format(self.algorithm, self.created_at, self.launcher)

    def as_dict(self):
        links_count = Link.objects.filter(algorithm_run=self.id).count()
        return {
            "algorithm": self.algorithm.as_dict(),
            "id": self.id,
            "created_at": self.created_at.timestamp() if self.created_at else None,
            "ended_at": self.ended_at.timestamp() if self.ended_at else None,
            "result": self.result,
            "finished": self.finished,
            "launcher": self.launcher.iaso_profile.as_dict() if self.launcher and self.launcher.iaso_profile else None,
            "destination": self.version_1.as_dict() if self.version_1 else None,
            "source": self.version_2.as_dict() if self.version_2 else None,
            "links_count": links_count,
        }

    def as_list(self):
        return {
            "algorithm_name": self.algorithm.name,
            "algorithm_id": self.algorithm.id,
            "id": self.id,
            "destination": self.version_1.as_list() if self.version_1 else None,
            "source": self.version_2.as_list() if self.version_2 else None,
        }


class Task(models.Model):
    """Represents an asynchronous function that will be run by a background worker for things like a data import"""

    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    progress_value = models.IntegerField(default=0)
    end_value = models.IntegerField(default=0)
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    launcher = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    result = models.JSONField(null=True, blank=True)
    status = models.CharField(choices=STATUS_TYPE_CHOICES, max_length=40, default=QUEUED)
    name = models.TextField()
    params = models.JSONField(null=True, blank=True)
    queue_answer = models.JSONField(null=True, blank=True)
    progress_message = models.TextField(null=True, blank=True)
    should_be_killed = models.BooleanField(default=False)
    external = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return "{} - {} - {} -{}".format(
            self.name,
            self.launcher,
            self.status,
            self.created_at,
        )

    def as_dict(self):
        return {
            "id": self.id,
            "created_at": self.created_at.timestamp() if self.created_at else None,
            "started_at": self.started_at.timestamp() if self.started_at else None,
            "ended_at": self.ended_at.timestamp() if self.ended_at else None,
            "params": self.params,
            "result": self.result,
            "status": self.status,
            "launcher": (
                self.launcher.iaso_profile.as_short_dict() if self.launcher and self.launcher.iaso_profile else None
            ),
            "progress_value": self.progress_value,
            "end_value": self.end_value,
            "name": self.name,
            "queue_answer": self.queue_answer,
            "progress_message": self.progress_message,
            "should_be_killed": self.should_be_killed,
        }

    def stop_if_killed(self):
        self.refresh_from_db()
        if self.should_be_killed:
            logger.warning(f"Stopping Task {self} as it as been marked for kill")
            self.status = KILLED
            self.ended_at = timezone.now()
            self.result = {"result": KILLED, "message": "Killed"}
            self.save()

    def report_progress_and_stop_if_killed(self, progress_value=None, progress_message=None, end_value=None):
        """Save progress and check if we have been killed
        We use a separate transaction, so we can report the progress even from a transaction, see services.py
        """
        logger.info(f"Task {self} reported {progress_message}")
        self.refresh_from_db()
        if self.should_be_killed:
            self.stop_if_killed()
            raise KilledException("Killed by user")

        if progress_value:
            self.progress_value = progress_value
        if progress_message:
            self.progress_message = progress_message
        if end_value:
            self.end_value = end_value
        self.save()

    def report_success_with_result(self, message=None, result_data=None):
        logger.info(f"Task {self} reported success with message {message}")
        self.progress_message = message
        self.status = SUCCESS
        self.ended_at = timezone.now()
        self.result = {"result": SUCCESS, "data": result_data}
        self.save()

    def report_success(self, message=None):
        logger.info(f"Task {self} reported success with message {message}")
        self.progress_message = message
        self.status = SUCCESS
        self.ended_at = timezone.now()
        self.result = {"result": SUCCESS, "message": message}
        self.save()


class Link(models.Model):
    destination = models.ForeignKey(
        "OrgUnit",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="source_set",
    )
    source = models.ForeignKey(
        "OrgUnit",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="destination_set",
    )
    validated = models.BooleanField(default=False)
    validator = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    validation_date = models.DateTimeField(auto_now=True, null=True, blank=True)

    similarity_score = models.SmallIntegerField(null=True)
    algorithm_run = models.ForeignKey(AlgorithmRun, on_delete=models.CASCADE, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "%s - %s - %s -%d" % (
            self.destination,
            self.source,
            self.algorithm_run,
            self.similarity_score,
        )

    def as_dict(self):
        return {
            "destination": self.destination.as_dict_with_parents(),
            "source": self.source.as_dict(),
            "id": self.id,
            "created_at": self.created_at.timestamp() if self.created_at else None,
            "updated_at": self.updated_at.timestamp() if self.updated_at else None,
            "validated": self.validated,
            "validator": (
                self.validator.iaso_profile.as_dict() if self.validator and self.validator.iaso_profile else None
            ),
            "validation_date": self.validation_date,
            "similarity_score": self.similarity_score,
            "algorithm_run": self.algorithm_run.as_dict() if self.algorithm_run else None,
        }

    def as_full_dict(self):
        return {
            "destination": self.destination.as_dict_with_parents(),
            "source": self.source.as_dict_with_parents(),
            "id": self.id,
            "created_at": self.created_at.timestamp() if self.created_at else None,
            "updated_at": self.updated_at.timestamp() if self.updated_at else None,
            "validated": self.validated,
            "validator": (
                self.validator.iaso_profile.as_dict() if self.validator and self.validator.iaso_profile else None
            ),
            "validation_date": self.validation_date,
            "similarity_score": self.similarity_score,
            "algorithm_run": self.algorithm_run.as_dict() if self.algorithm_run else None,
        }


GROUP_DOMAIN = [
    ("POLIO", _("Polio")),
]


class DefaultGroupManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(domain=None)

    def filter_for_user(self, user: User):
        profile = user.iaso_profile
        queryset = self
        version_ids = (
            SourceVersion.objects.filter(data_source__projects__account=profile.account)
            .values_list("id", flat=True)
            .distinct()
        )
        queryset = queryset.filter(source_version_id__in=version_ids)
        return queryset


class DomainGroupManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(domain__isnull=False)


class Group(models.Model):
    """Group of OrgUnit.

    Linked to a source_version, which is also used for tenancy"""

    name = models.TextField()
    source_ref = models.TextField(null=True, blank=True)
    org_units = models.ManyToManyField("OrgUnit", blank=True, related_name="groups")
    domain = models.CharField(max_length=10, choices=GROUP_DOMAIN, null=True, blank=True)
    block_of_countries = models.BooleanField(
        default=False
    )  # This field is used to mark a group containing only countries
    # The migration 0086_add_version_constraints add a constraint to ensure that the source version
    # is the same between the orgunit and the group
    source_version = models.ForeignKey(SourceVersion, null=True, blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = DefaultGroupManager()
    all_objects = models.Manager()
    domain_objects = DomainGroupManager()

    class Meta:
        base_manager_name = "all_objects"

    def __str__(self):
        return "{} | {} ".format(self.name, self.source_version)

    def as_small_dict(self):
        return {
            "id": self.id,
            "name": self.name,
        }

    def as_dict(self, with_counts=True):
        res = {
            "id": self.id,
            "name": self.name,
            "source_ref": self.source_ref,
            "created_at": self.created_at.timestamp() if self.created_at else None,
            "updated_at": self.updated_at.timestamp() if self.updated_at else None,
            "source_version": self.source_version_id,
            "block_of_countries": self.block_of_countries,  # This field is used to mark a group containing only countries
        }

        if with_counts:
            res["org_unit_count"] = self.org_units.count()

        return res


class GroupSetQuerySet(models.QuerySet):
    def filter_for_user_and_app_id(
        self, user: typing.Union[User, AnonymousUser, None], app_id: typing.Optional[str] = None
    ):
        queryset = self
        if user and user.is_anonymous and app_id is None:
            return self.none()

        if user and user.is_authenticated:
            # avoid creating duplicated record by joining projects's datasources
            version_ids = (
                SourceVersion.objects.filter(data_source__projects__account=user.iaso_profile.account)
                .values_list("id", flat=True)
                .distinct()
            )
            queryset = queryset.filter(source_version_id__in=version_ids)

        if app_id is not None:
            try:
                project = Project.objects.get_for_user_and_app_id(user, app_id)

                queryset = queryset.filter(source_version__data_source__projects__in=[project])

            except Project.DoesNotExist:
                return self.none()

        return queryset

    def prefetch_source_version_details(self):
        queryset = self
        queryset = queryset.prefetch_related("source_version")
        queryset = queryset.prefetch_related("source_version__data_source")
        return queryset

    def prefetch_groups_details(self):
        queryset = self
        queryset = queryset.prefetch_related("groups__source_version")
        queryset = queryset.prefetch_related("groups__source_version__data_source")
        return queryset


GroupSetManager = models.Manager.from_queryset(GroupSetQuerySet)


class GroupSet(models.Model):
    class GroupBelonging(models.TextChoices):
        SINGLE = "SINGLE", _("SINGLE")
        MULTIPLE = "MULTIPLE", _("MULTIPLE")

    name = models.TextField()
    source_ref = models.TextField(null=True, blank=True)
    source_version = models.ForeignKey(SourceVersion, null=True, blank=True, on_delete=models.CASCADE)
    groups = models.ManyToManyField(Group, blank=True, related_name="group_sets")
    group_belonging = models.TextField(
        choices=GroupBelonging.choices, default=GroupBelonging.SINGLE, null=False, blank=False, max_length=10
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = GroupSetManager()

    def __str__(self):
        return "{} | {} ".format(self.name, self.source_version)


class Mapping(models.Model):
    name = models.TextField()
    data_source = models.ForeignKey(DataSource, on_delete=models.CASCADE, related_name="mappings")
    form = models.ForeignKey("Form", on_delete=models.DO_NOTHING, null=True, blank=True)
    mapping_type = models.TextField(choices=MAPPING_TYPE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "{} {}".format(self.form, self.mapping_type)

    def is_aggregate(self):
        return self.mapping_type == AGGREGATE

    def is_event_tracker(self):
        return self.mapping_type == EVENT_TRACKER

    def is_simple_event(self):
        return self.mapping_type == EVENT

    def as_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "data_source": self.data_source.as_dict(),
            "form": self.form.as_dict(),
            "mapping_type": self.mapping_type,
            "created_at": self.created_at.timestamp() if self.created_at else None,
            "updated_at": self.updated_at.timestamp() if self.updated_at else None,
        }


class MappingVersion(models.Model):
    QUESTION_MAPPING_NEVER_MAPPED = "neverMapped"
    QUESTION_MAPPING_MULTIPLE = "multiple"

    EVENT_DATE_SOURCE_FROM_SUBMISSION_CREATED_AT = "FROM_SUBMISSION_CREATED_AT"
    EVENT_DATE_SOURCE_FROM_SUBMISSION_PERIOD = "FROM_SUBMISSION_PERIOD"

    form_version = models.ForeignKey("FormVersion", on_delete=models.CASCADE, related_name="mapping_versions")
    mapping = models.ForeignKey(
        Mapping,
        on_delete=models.CASCADE,
        related_name="versions",
        null=True,
        blank=True,
    )
    name = models.TextField()
    json = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [["form_version", "name"]]

    def __str__(self):
        return "{} - {}".format(self.form_version, self.name)

    def as_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at.timestamp() if self.created_at else None,
            "updated_at": self.updated_at.timestamp() if self.updated_at else None,
        }

    @staticmethod
    def get_event_date_source(json):
        if "event_date_source" in json:
            return json["event_date_source"]
        return MappingVersion.EVENT_DATE_SOURCE_FROM_SUBMISSION_CREATED_AT


class ExternalCredentials(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="credentials")

    name = models.TextField()
    login = models.TextField()
    password = models.TextField()
    url = models.TextField()

    @property
    def is_valid(self) -> bool:
        return bool(self.url and self.password and self.login)

    def __str__(self):
        return "{} - {} - {} ({})".format(self.name, self.login, self.url, self.account)

    def as_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "login": self.login,
            "url": self.url,
            "is_valid": self.is_valid,
        }


class InstanceQuerySet(django_cte.CTEQuerySet):
    def with_lock_info(self, user):
        """
        Annotate the QuerySet with the lock info for the given user.

        The following fields are added to the queryset:
        - lock_applying_to_user
        - count_lock_applying_to_user: number of locks that prevent user to modify the instance
        - count_active_lock: number of locks on instance that are not unlocked

        Implementation: we decided to make the lock calculation via annotations, so it's a lot faster with large querysets.
        """

        user_org_unit_ids = list(OrgUnit.objects.filter_for_user(user).values_list("id", flat=True))

        return (
            self.annotate(
                lock_applying_to_user=FilteredRelation(
                    "instancelock",
                    condition=Q(
                        ~Q(instancelock__top_org_unit_id__in=user_org_unit_ids),
                        Q(instancelock__unlocked_by__isnull=True),
                    ),
                )
            )
            .annotate(count_lock_applying_to_user=Count("lock_applying_to_user"))
            .annotate(count_active_lock=Count("instancelock", Q(instancelock__unlocked_by__isnull=True)))
        )

    def with_status(self):
        duplicates_subquery = (
            self.values("period", "form", "org_unit")
            .annotate(ids=ArrayAgg("id"))
            .annotate(
                c=models.Func(
                    "ids",
                    models.Value(1, output_field=models.IntegerField()),
                    function="array_length",
                    output_field=models.IntegerField(),
                )
            )
            .filter(form__in=Form.objects.filter(single_per_period=True))
            .filter(c__gt=1)
            .annotate(id=models.Func("ids", function="unnest"))
            .values("id")
        )

        return self.annotate(
            status=models.Case(
                models.When(
                    id__in=duplicates_subquery,
                    then=models.Value(Instance.STATUS_DUPLICATED),
                ),
                models.When(
                    last_export_success_at__isnull=False,
                    then=models.Value(Instance.STATUS_EXPORTED),
                ),
                default=models.Value(Instance.STATUS_READY),
                output_field=models.CharField(),
            )
        )

    def with_status_alternate(self):  # TODO: probably not needed
        duplicates_subquery = (
            self.exclude(id=models.OuterRef("id"))
            .filter(
                form_id=models.OuterRef("form_id"),
                org_unit_id=models.OuterRef("org_unit_id"),
                period=models.OuterRef("period"),
            )
            .values("form_id", "org_unit_id", "period")
            .annotate(duplicates_count=models.Count("*"))
        )

        qs = self.annotate(
            duplicates_count=models.Subquery(
                duplicates_subquery.values("duplicates_count"),
                output_field=models.IntegerField(),
            )
        )

        return qs.annotate(
            status=models.Case(
                models.When(
                    duplicates_count__gt=0,
                    then=models.Value(Instance.STATUS_DUPLICATED),
                ),
                models.When(
                    last_export_success_at__isnull=False,
                    then=models.Value(Instance.STATUS_EXPORTED),
                ),
                default=models.Value(Instance.STATUS_READY),
                output_field=models.CharField(),
            )
        )

    def counts_by_status(self):
        grouping_fields = ["period", "form_id", "form__name", "form__form_id"]

        return (
            self.values(*grouping_fields)
            .annotate(total_count=models.Count("id", distinct=True))
            .annotate(
                duplicated_count=models.Count(
                    "id",
                    distinct=True,
                    filter=models.Q(status=Instance.STATUS_DUPLICATED),
                )
            )
            .annotate(
                exported_count=models.Count(
                    "id",
                    distinct=True,
                    filter=models.Q(status=Instance.STATUS_EXPORTED),
                )
            )
            .annotate(ready_count=models.Count("id", distinct=True, filter=models.Q(status=Instance.STATUS_READY)))
            .exclude(period=None)
            .exclude(period="")
            .order_by("period", "form__name")
        )

    def for_filters(
        self,
        form_id=None,
        form_ids=None,
        with_location=None,
        org_unit_type_id=None,
        device_id=None,
        device_ownership_id=None,
        org_unit_parent_id=None,
        org_unit_id=None,
        period_ids=None,
        periods_bound=None,
        status=None,
        instance_id=None,
        search=None,
        created_from=None,
        created_to=None,
        show_deleted=None,
        entity_id=None,
        user_ids=None,
        modification_from=None,
        modification_to=None,
        sent_from=None,
        sent_to=None,
        json_content=None,
        planning_ids=None,
        project_ids=None,
        only_reference=None,
    ):
        queryset = self

        if created_from or created_to:
            queryset = queryset.annotate(creation_timestamp=Coalesce("source_created_at", "created_at"))
            if created_from:
                queryset = queryset.filter(creation_timestamp__gte=created_from)
            if created_to:
                queryset = queryset.filter(creation_timestamp__lte=created_to)

        if period_ids:
            if isinstance(period_ids, str):
                period_ids = period_ids.split(",")
            queryset = queryset.filter(period__in=period_ids)
        if periods_bound:
            if periods_bound[0]:
                queryset = queryset.filter(period__gte=periods_bound[0])
            if periods_bound[1]:
                queryset = queryset.filter(period__lte=periods_bound[1])

        if instance_id:
            queryset = queryset.filter(id=instance_id)

        if org_unit_type_id:
            queryset = queryset.filter(org_unit__org_unit_type__in=org_unit_type_id.split(","))

        if only_reference == "true":
            if org_unit_id:
                # Create a subquery for OrgUnitReferenceInstance that checks for matching org_unit_id and instance_id
                subquery = OrgUnitReferenceInstance.objects.filter(org_unit_id=org_unit_id, instance_id=OuterRef("pk"))
                queryset = queryset.annotate(has_reference=Exists(subquery)).filter(has_reference=True)
            else:
                # If no specific org_unit_id is provided, check for any OrgUnitReferenceInstance matching the instance_id
                subquery = OrgUnitReferenceInstance.objects.filter(instance_id=OuterRef("pk"))
                queryset = queryset.annotate(has_reference=Exists(subquery)).filter(has_reference=True)
        else:
            if org_unit_id:
                # Filter by org unit id if only_reference is not true
                queryset = queryset.filter(org_unit_id=org_unit_id)

        if org_unit_parent_id:
            # Local import to avoid loop
            from iaso.models import OrgUnit

            parent = OrgUnit.objects.get(id=org_unit_parent_id)
            queryset = queryset.filter(org_unit__path__descendants=parent.path)
        if with_location == "true":
            queryset = queryset.filter(location__isnull=False)

        if with_location == "false":
            queryset = queryset.filter(location__isnull=True)

        if device_id:
            queryset = queryset.filter(device__id=device_id)

        if device_ownership_id:
            device_ownership = get_object_or_404(DeviceOwnership, pk=device_ownership_id)
            queryset = queryset.filter(device__id=device_ownership.device.id)

        if form_id:
            queryset = queryset.filter(form_id=form_id)

        if form_ids:
            queryset = queryset.filter(form_id__in=form_ids.split(","))

        if show_deleted:
            queryset = queryset.filter(deleted=True)
        else:
            # whatever don't show deleted submissions
            queryset = queryset.exclude(deleted=True)

        if entity_id:
            queryset = queryset.filter(entity_id=entity_id)

        if planning_ids:
            queryset = queryset.filter(planning_id__in=planning_ids.split(","))

        if project_ids:
            queryset = queryset.filter(project_id__in=project_ids.split(","))

        if search:
            if search.startswith("ids:"):
                ids_str = search.replace("ids:", "")
                try:
                    ids = [int(i.strip()) for i in ids_str.split(",")]
                    queryset = queryset.filter(id__in=ids)
                except:
                    queryset = queryset.filter(id__in=[])
                    print("Failed parsing ids in search", search)
            elif search.startswith("refs:"):
                s = search.replace("refs:", "")
                try:
                    refs = re.findall("[A-Za-z0-9_-]+", s)
                    queryset = queryset.filter(org_unit__source_ref__in=refs)
                except:
                    print("Failed parsing refs in search", search)
            else:
                queryset = queryset.filter(
                    Q(org_unit__name__icontains=search) | Q(org_unit__aliases__contains=[search])
                )
        # add status annotation
        queryset = queryset.with_status()

        if modification_from:
            queryset = queryset.filter(updated_at__gte=modification_from)
        if modification_to:
            queryset = queryset.filter(updated_at__lte=modification_to)

        if sent_from:
            queryset = queryset.filter(created_at__gte=sent_from)
        if sent_to:
            queryset = queryset.filter(created_at__lte=sent_to)

        if status:
            statuses = status.split(",")
            queryset = queryset.filter(status__in=statuses)

        if user_ids:
            queryset = queryset.filter(created_by__id__in=user_ids.split(","))

        if json_content:
            q = jsonlogic_to_q(jsonlogic=json_content, field_prefix="json__")
            queryset = queryset.filter(q)

        return queryset

    def for_org_unit_hierarchy(self, org_unit):
        # TODO: we could write our own descendants lookup instead of using the one provided in django-ltree
        # TODO: as it does not handle arrays of path (ltree does)
        # We need to cast PathValue instances to strings - this could be fixed upstream
        # (https://github.com/mariocesar/django-ltree/issues/8)
        if isinstance(org_unit, list):
            query = reduce(
                operator.or_,
                [Q(org_unit__path__descendants=str(ou.path)) for ou in org_unit],
            )
        else:
            query = Q(org_unit__path__descendants=str(org_unit.path))

        return self.filter(query)

    def filter_for_user(self, user):
        profile = user.iaso_profile
        # Do a relative import to avoid an import loop
        from .org_unit import OrgUnit

        new_qs = self

        # If user is restricted to some org unit, filter on thoses
        if profile.org_units.exists():
            orgunits = OrgUnit.objects.hierarchy(profile.org_units.all())

            new_qs = new_qs.filter(org_unit__in=orgunits)
        new_qs = new_qs.filter(project__account_id=profile.account_id)
        return new_qs


class NonDeletedInstanceManager(models.Manager):
    def get_queryset(self):
        """
        Exclude soft deleted instances from all results.
        """
        return super().get_queryset().filter(deleted=False)


class Instance(models.Model):
    """A series of answers by an individual for a specific form

    Note that instances are called "Submissions" in the UI
    """

    UPLOADED_TO = "instances/"

    STATUS_READY = "READY"
    STATUS_DUPLICATED = "DUPLICATED"
    STATUS_EXPORTED = "EXPORTED"

    ALWAYS_ALLOWED_PATHS_XML = {
        "formhub",
        "formhub/uuid",
        "meta",
        "meta/instanceID",
        "meta/editUserID",
        "meta/deprecatedID",
    }

    REFERENCE_FLAG_CODE = "flag"
    REFERENCE_UNFLAG_CODE = "unflag"

    # Previously created_at and update_at were filled by the mobile, now they
    # have been replaced by `source_created_at` and `update_created_at`.
    # Columns `created_at` and `update_at` are set by Django per usual.
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    source_created_at = models.DateTimeField(null=True, blank=True, help_text="Creation time on the device")
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, blank=True, null=True)
    last_modified_by = models.ForeignKey(
        User, on_delete=models.PROTECT, blank=True, null=True, related_name="last_modified_by"
    )
    updated_at = models.DateTimeField(auto_now=True, editable=False)
    source_updated_at = models.DateTimeField(null=True, blank=True, help_text="Update time on the device")
    uuid = models.TextField(null=True, blank=True)
    export_id = models.TextField(null=True, blank=True, default=generate_id_for_dhis_2)
    correlation_id = models.BigIntegerField(null=True, blank=True)
    name = models.TextField(null=True, blank=True)  # form.name
    file = models.FileField(upload_to=UPLOADED_TO, null=True, blank=True)
    file_name = models.TextField(null=True, blank=True)
    location = PointField(null=True, blank=True, dim=3, srid=4326)
    org_unit = models.ForeignKey("OrgUnit", on_delete=models.DO_NOTHING, null=True, blank=True)
    form = models.ForeignKey(
        "Form",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="instances",
    )
    project = models.ForeignKey("Project", blank=True, null=True, on_delete=models.DO_NOTHING)
    json = models.JSONField(null=True, blank=True)
    accuracy = models.DecimalField(null=True, blank=True, decimal_places=2, max_digits=7)
    device = models.ForeignKey("Device", null=True, blank=True, on_delete=models.DO_NOTHING)
    period = models.TextField(null=True, blank=True, db_index=True)
    entity = models.ForeignKey("Entity", null=True, blank=True, on_delete=models.DO_NOTHING, related_name="instances")
    planning = models.ForeignKey("Planning", null=True, blank=True, on_delete=models.SET_NULL, related_name="instances")
    form_version = models.ForeignKey(
        "FormVersion", null=True, blank=True, on_delete=models.DO_NOTHING, related_name="form_version"
    )

    last_export_success_at = models.DateTimeField(null=True, blank=True)

    objects = models.Manager.from_queryset(InstanceQuerySet)()
    non_deleted_objects = NonDeletedInstanceManager.from_queryset(InstanceQuerySet)()

    # Is instance SoftDeleted. It doesn't use the SoftDeleteModel deleted_at like the rest for historical reason.
    deleted = models.BooleanField(default=False)
    # See public_create_url workflow in enketo/README.md. used to tell we should export immediately
    to_export = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["updated_at"]),
            models.Index(fields=["source_created_at"]),
            models.Index(fields=["source_updated_at"]),
        ]

    def __str__(self):
        return "{} {} {}".format(self.id, self.form, self.name)

    @property
    def is_instance_of_reference_form(self) -> bool:
        if not self.org_unit or not self.org_unit.org_unit_type:
            return False
        return self.org_unit.org_unit_type.reference_forms.filter(id=self.form_id).exists()

    @property
    def is_reference_instance(self) -> bool:
        if not self.org_unit:
            return False
        return self.org_unit.reference_instances.filter(orgunitreferenceinstance__instance=self).exists()

    @property
    def source_created_at_with_fallback(self):
        return self.source_created_at if self.source_created_at else self.created_at

    @property
    def source_updated_at_with_fallback(self):
        return self.source_updated_at if self.source_updated_at else self.updated_at

    def flag_reference_instance(self, org_unit: "OrgUnit") -> "OrgUnitReferenceInstance":
        if not self.form:
            raise ValidationError(_("The Instance must be linked to a Form."))
        if not org_unit.org_unit_type:
            raise ValidationError(_("The OrgUnit must be linked to a OrgUnitType."))
        if not org_unit.org_unit_type.reference_forms.filter(id=self.form_id).exists():
            raise ValidationError(_("The submission must be an instance of a reference form."))
        kwargs = {"org_unit": org_unit, "form_id": self.form_id}
        # Delete the previous flag for this pair of org_unit/form.
        OrgUnitReferenceInstance.objects.filter(**kwargs).delete()
        # Flag the new one.
        return OrgUnitReferenceInstance.objects.create(instance=self, **kwargs)

    def unflag_reference_instance(self, org_unit: "OrgUnit") -> None:
        org_unit.reference_instances.remove(self)

    # Used by Django Admin to link to the submission page in the dashboard
    def get_absolute_url(self):
        return f"/dashboard/forms/submission/instanceId/{self.pk}"

    def convert_location_from_field(self, field_name=None):
        f = field_name
        if f is None:
            f = self.form.location_field

            location = self.json.get(f, None)
            if location:
                latitude, longitude, altitude, accuracy = (float(x) for x in location.split(" "))
                self.location = Point(x=longitude, y=latitude, z=altitude, srid=4326)
                self.accuracy = accuracy
                self.save()

    def convert_device(self):
        if self.json and not self.device:
            device_field = self.form.device_field
            if not device_field:
                device_field = "deviceid"
            imei = self.json.get(device_field, None)
            if imei is not None:
                device, created = Device.objects.get_or_create(imei=imei)
                self.device = device
                self.save()
                if self.project:
                    self.device.projects.add(self.project)

    def convert_correlation(self):
        if not self.correlation_id:
            identifier = str(self.id)
            if self.form.correlation_field and self.json:
                identifier += self.json.get(self.form.correlation_field, None)
                identifier = identifier.zfill(3)
            random_number = random.choice("1234567890")
            value = int(identifier + random_number)
            suffix = "{:02d}".format(value % 97)
            self.correlation_id = identifier + random_number + suffix
            self.save()

    def xml_file_to_json(self, file: typing.IO) -> typing.Dict[str, typing.Any]:
        raw_content = file.read().decode("utf-8")
        fixed_content = fix_emoji(raw_content).decode("utf-8")
        copy_io_utf8 = StringIO(fixed_content)
        soup = Soup(copy_io_utf8, "lxml-xml", from_encoding="utf-8")

        form_version_id = extract_form_version_id(soup)
        if form_version_id:
            # TODO: investigate: can self.form be None here? What's the expected behavior?
            form_versions = self.form.form_versions.filter(version_id=form_version_id)  # type: ignore
            form_version = form_versions.first()
            if form_version:
                questions_by_path = form_version.questions_by_path()
                allowed_paths = set(questions_by_path.keys())
                allowed_paths.update(self.ALWAYS_ALLOWED_PATHS_XML)
                flat_results = flat_parse_xml_soup(
                    soup, [rg["name"] for rg in form_version.repeat_groups()], allowed_paths
                )
                if len(flat_results["skipped_paths"]) > 0:
                    logger.warning(
                        f"skipped {len(flat_results['skipped_paths'])} paths while parsing instance {self.id}",
                        flat_results,
                    )
                return flat_results["flat_json"]
            else:
                # warn old form, but keep it working ? or throw error
                return flat_parse_xml_soup(soup, [], None)["flat_json"]
        else:
            return flat_parse_xml_soup(soup, [], None)["flat_json"]

    def get_and_save_json_of_xml(self, force=False, tries=3):
        """
        Convert the xml file to json and save it to the instance.
        If the instance already has a json, don't do anything unless `force=True`.

        When downloading from S3, attempt `tries` times (3 by default) with
        exponential backoff.

        :return: in all cases, return the JSON representation of the instance
        """
        if self.json and not force:
            # already converted, we can use this one
            return self.json
        elif self.file:
            # not converted yet, but we have a file, so we can convert it
            if "amazonaws" in self.file.url:
                for i in range(tries):
                    try:
                        file = urlopen(self.file.url)
                        break
                    except HTTPError as err:
                        if err.code == 503:  # Slow Down
                            time.sleep(2**i)
                        else:
                            raise err

            else:
                file = self.file

            self.json = self.xml_file_to_json(file)
            self.save()
            return self.json
        else:
            # no file, no json, when/why does this happen?
            return {}

    def get_form_version(self):
        json = self.get_and_save_json_of_xml()

        try:
            return self.form.form_versions.get(version_id=json["_version"])
        except (KeyError, FormVersion.DoesNotExist):
            return None

    def export(self, launcher=None, force_export=False):
        from iaso.dhis2.datavalue_exporter import DataValueExporter
        from iaso.dhis2.export_request_builder import ExportRequestBuilder, NothingToExportError

        try:
            export_request = ExportRequestBuilder().build_export_request(
                filters={"instance_id": self.id},
                launcher=launcher,
                force_export=force_export,
            )

            DataValueExporter().export_instances(export_request)
            self.refresh_from_db()
        except NothingToExportError:
            print("Export failed for instance", self)

    def as_dict(self):
        file_content = self.get_and_save_json_of_xml()
        last_modified_by = None

        if self.last_modified_by is not None:
            last_modified_by = self.last_modified_by.username

        return {
            "uuid": self.uuid,
            "export_id": self.export_id,
            "file_name": self.file_name,
            "file_content": file_content,
            "file_url": self.file.url if self.file else None,
            "id": self.id,
            "form_id": self.form_id,
            "form_name": self.form.name if self.form else None,
            "created_at": self.created_at.timestamp(),
            "updated_at": self.updated_at.timestamp(),
            "source_created_at": self.source_created_at.timestamp() if self.source_created_at else None,
            "source_updated_at": self.source_updated_at.timestamp() if self.source_updated_at else None,
            "org_unit": self.org_unit.as_dict() if self.org_unit else None,
            "latitude": self.location.y if self.location else None,
            "longitude": self.location.x if self.location else None,
            "altitude": self.location.z if self.location else None,
            "period": self.period,
            "project_name": self.project.name if self.project else None,
            "status": getattr(self, "status", None),
            "correlation_id": self.correlation_id,
            "created_by": (
                {
                    "username": self.created_by.username,
                    "first_name": self.created_by.first_name,
                    "last_name": self.created_by.last_name,
                }
                if self.created_by
                else None
            ),
            "last_modified_by": last_modified_by,
        }

    def as_dict_with_descriptor(self):
        dict = self.as_dict()
        form_version = self.get_form_version()
        dict["form_descriptor"] = form_version.get_or_save_form_descriptor() if form_version is not None else None
        return dict

    def as_full_model(self, with_entity=False):
        file_content = self.get_and_save_json_of_xml()
        form_version = self.get_form_version()

        last_modified_by = None
        if self.last_modified_by is not None:
            last_modified_by = self.last_modified_by.username

        result = {
            "uuid": self.uuid,
            "last_modified_by": last_modified_by,
            "modification": True,
            "id": self.id,
            "device_id": self.device.imei if self.device else None,
            "file_name": self.file_name,
            "file_url": self.file.url if self.file else None,
            "form_id": self.form_id,
            "form_version_id": self.form_version.id if self.form_version else None,
            "form_name": self.form.name,
            "form_descriptor": form_version.get_or_save_form_descriptor() if form_version is not None else None,
            "created_at": self.created_at.timestamp(),
            "updated_at": self.updated_at.timestamp(),
            "source_created_at": self.source_created_at.timestamp() if self.source_created_at else None,
            "source_updated_at": self.source_updated_at.timestamp() if self.source_updated_at else None,
            "org_unit": self.org_unit.as_dict_with_parents(light=False, light_parents=False) if self.org_unit else None,
            "latitude": self.location.y if self.location else None,
            "longitude": self.location.x if self.location else None,
            "altitude": self.location.z if self.location else None,
            "accuracy": self.accuracy,
            "period": self.period,
            "planning_id": self.planning.id if self.planning else None,
            "planning_name": self.planning.name if self.planning else None,
            "team_id": self.planning.team_id if self.planning else None,
            "file_content": file_content,
            "files": [f.file.url if f.file else None for f in self.instancefile_set.filter(deleted=False)],
            "status": getattr(self, "status", None),
            "correlation_id": self.correlation_id,
            "last_export_success_at": self.last_export_success_at.timestamp() if self.last_export_success_at else None,
            "export_id": self.export_id,
            "export_statuses": [
                {
                    "status": export_status.status,
                    "created_at": export_status.created_at.timestamp() if export_status.created_at else None,
                    "export_request": {
                        "launcher": {
                            "full_name": (
                                export_status.export_request.launcher.get_full_name()
                                if export_status.export_request.launcher
                                else "AUTO UPLOAD"
                            ),
                            "email": (
                                export_status.export_request.launcher.email
                                if export_status.export_request.launcher
                                else "AUTO UPLOAD"
                            ),
                        },
                        "last_error_message": f"{export_status.last_error_message}, {export_status.export_request.last_error_message}",
                    },
                }
                for export_status in Paginator(self.exportstatus_set.order_by("-id"), 3).object_list
            ],
            "deleted": self.deleted,
            "created_by": (
                {
                    "username": self.created_by.username,
                    "first_name": self.created_by.first_name,
                    "last_name": self.created_by.last_name,
                }
                if self.created_by
                else None
            ),
        }

        result["change_requests"] = self.get_instance_change_requests_data()

        if with_entity and self.entity_id:
            result["entity"] = self.entity.as_small_dict_with_nfc_cards(self)

        return result

    def get_instance_change_requests_data(self):
        from iaso.api.org_unit_change_requests.serializers import OrgUnitChangeRequestListSerializer

        org_unit_change_requests = self.orgunitchangerequest_set.all()
        serializer = OrgUnitChangeRequestListSerializer(org_unit_change_requests, many=True)

        return serializer.data

    def as_small_dict(self):
        return {
            "id": self.id,
            "file_url": self.file.url if self.file else None,
            "created_at": self.source_created_at_with_fallback.timestamp(),
            "updated_at": self.source_updated_at_with_fallback.timestamp(),
            "period": self.period,
            "latitude": self.location.y if self.location else None,
            "longitude": self.location.x if self.location else None,
            "altitude": self.location.z if self.location else None,
            "accuracy": self.accuracy,
            "files": [f.file.url if f.file else None for f in self.instancefile_set.filter(deleted=False)],
            "status": getattr(self, "status", None),
            "correlation_id": self.correlation_id,
        }

    def soft_delete(self):
        self.deleted = True
        self.save()

    def restore(self):
        self.deleted = False
        self.save()

    def can_user_modify(self, user):
        """Check only for lock, assume user have other perms"""
        # active locks for instance
        locks = self.instancelock_set.filter(unlocked_by__isnull=True)
        # highest lock
        highest_lock = locks.order_by("top_org_unit__path__depth").first()
        if not highest_lock:
            # No lock anyone can modify
            return True

        # can user access this orgunit
        from iaso.models import OrgUnit  # Local import to prevent loop

        if OrgUnit.objects.filter_for_user(user).filter(id=highest_lock.top_org_unit_id).exists():
            return True
        return False

    @property
    def has_org_unit(self):
        return self.org_unit if self.org_unit else None

    def save(self, *args, **kwargs):
        if self.json is not None and self.json.get("_version"):
            try:
                form_version = FormVersion.objects.get(version_id=self.json.get("_version"), form_id=self.form.id)
                self.form_version = form_version
            except ObjectDoesNotExist:
                pass
        return super().save(*args, **kwargs)


class InstanceFile(models.Model):
    UPLOADED_TO = "instancefiles/"
    instance = models.ForeignKey(Instance, on_delete=models.DO_NOTHING, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    name = models.TextField(null=True, blank=True)
    file = models.FileField(upload_to=UPLOADED_TO, null=True, blank=True)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return "{} ".format(self.name)

    def as_dict(self):
        return {
            "id": self.id,
            "instance_id": self.instance_id,
            "file": self.file.url if self.file else None,
            "created_at": self.created_at.timestamp() if self.created_at else None,
            "file_type": get_file_type(self.file),
        }


class ProfileQuerySet(models.QuerySet):
    def with_editable_org_unit_types(self):
        qs = self
        return qs.annotate(
            annotated_editable_org_unit_types_ids=ArrayAgg(
                "editable_org_unit_types__id", distinct=True, filter=Q(editable_org_unit_types__isnull=False)
            ),
            annotated_user_roles_editable_org_unit_type_ids=ArrayAgg(
                "user_roles__editable_org_unit_types__id",
                distinct=True,
                filter=Q(user_roles__editable_org_unit_types__isnull=False),
            ),
        )


class Profile(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="iaso_profile")
    external_user_id = models.CharField(max_length=512, null=True, blank=True)
    organization = models.CharField(max_length=512, null=True, blank=True)
    # Each profile/user has access to multiple orgunits. Having access to OU also give access to all its children
    org_units = models.ManyToManyField("OrgUnit", blank=True, related_name="iaso_profile")
    language = models.CharField(max_length=512, null=True, blank=True)
    dhis2_id = models.CharField(max_length=128, null=True, blank=True, help_text="Dhis2 user ID for SSO Auth")
    home_page = models.CharField(max_length=512, null=True, blank=True)
    user_roles = models.ManyToManyField("UserRole", related_name="iaso_profile", blank=True)
    projects = models.ManyToManyField("Project", related_name="iaso_profile", blank=True)
    phone_number = PhoneNumberField(blank=True)
    # Each user can have restricted write access to OrgUnits, based on their type.
    # By default, empty `editable_org_unit_types` means access to everything.
    editable_org_unit_types = models.ManyToManyField(
        "OrgUnitType", related_name="editable_by_iaso_profile_set", blank=True
    )

    objects = models.Manager.from_queryset(ProfileQuerySet)()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["dhis2_id", "account"], name="dhis2_id_constraint")]

    def __str__(self):
        return "{} -- {}".format(self.user, self.account)

    def get_hierarchy_for_user(self):
        return OrgUnit.objects.filter_for_user_and_app_id(self.user)

    def get_user_roles_editable_org_unit_type_ids(self):
        try:
            return self.annotated_user_roles_editable_org_unit_type_ids
        except AttributeError:
            return list(
                self.user_roles.values_list("editable_org_unit_types__id", flat=True)
                .distinct("id")
                .exclude(editable_org_unit_types__id__isnull=True)
            )

    def as_dict(self, small=False):
        user_roles = self.user_roles.all()
        user_group_permissions = list(
            map(lambda permission: permission.split(".")[1], list(self.user.get_group_permissions()))
        )
        user_permissions = list(
            self.user.user_permissions.filter(codename__startswith="iaso_").values_list("codename", flat=True)
        )
        all_permissions = user_group_permissions + user_permissions
        permissions = list(set(all_permissions))
        try:
            editable_org_unit_type_ids = self.annotated_editable_org_unit_types_ids
        except AttributeError:
            editable_org_unit_type_ids = [out.pk for out in self.editable_org_unit_types.all()]

        user_roles_editable_org_unit_type_ids = self.get_user_roles_editable_org_unit_type_ids()

        other_accounts = []
        user_infos = self.user
        if hasattr(self.user, "tenant_user"):
            other_accounts = self.user.tenant_user.get_other_accounts()
            user_infos = self.user.tenant_user.main_user

        result = {
            "id": self.id,
            "first_name": user_infos.first_name,
            "user_name": user_infos.username,
            "last_name": user_infos.last_name,
            "email": user_infos.email,
            "permissions": permissions,
            "user_permissions": user_permissions,
            "is_superuser": self.user.is_superuser,
            "user_roles": list(role.id for role in user_roles),
            "user_roles_permissions": list(role.as_dict() for role in user_roles),
            "language": self.language,
            "organization": self.organization,
            "user_id": self.user.id,
            "dhis2_id": self.dhis2_id,
            "home_page": self.home_page,
            "phone_number": self.phone_number.as_e164 if self.phone_number else None,
            "country_code": region_code_for_number(self.phone_number).lower() if self.phone_number else None,
            "projects": [p.as_dict() for p in self.projects.all().order_by("name")],
            "other_accounts": [account.as_dict() for account in other_accounts],
            "editable_org_unit_type_ids": editable_org_unit_type_ids,
            "user_roles_editable_org_unit_type_ids": user_roles_editable_org_unit_type_ids,
        }

        if small:
            return result | {
                "org_units": [o.as_very_small_dict() for o in self.org_units.all()],
            }
        else:
            return result | {
                "account": self.account.as_small_dict(),
                "org_units": [o.as_small_dict() for o in self.org_units.all().order_by("name")],
            }

    def as_short_dict(self):
        try:
            editable_org_unit_type_ids = self.annotated_editable_org_unit_types_ids
        except AttributeError:
            editable_org_unit_type_ids = [out.pk for out in self.editable_org_unit_types.all()]

        user_roles_editable_org_unit_type_ids = self.get_user_roles_editable_org_unit_type_ids()

        user_infos = self.user
        if hasattr(self.user, "tenant_user") and self.user.tenant_user:
            user_infos = self.user.tenant_user.main_user

        return {
            "id": self.id,
            "first_name": user_infos.first_name,
            "user_name": user_infos.username,
            "last_name": user_infos.last_name,
            "email": user_infos.email,
            "language": self.language,
            "user_id": self.user.id,
            "phone_number": self.phone_number.as_e164 if self.phone_number else None,
            "country_code": region_code_for_number(self.phone_number).lower() if self.phone_number else None,
            "editable_org_unit_type_ids": editable_org_unit_type_ids,
            "user_roles_editable_org_unit_type_ids": user_roles_editable_org_unit_type_ids,
        }

    def has_a_team(self):
        team = self.user.teams.filter(deleted_at=None).first()
        if team:
            return True
        return False

    def get_editable_org_unit_type_ids(self) -> set[int]:
        ids_in_user_roles = set(
            self.user_roles.exclude(editable_org_unit_types__isnull=True).values_list(
                "editable_org_unit_types", flat=True
            )
        )
        ids_in_user_profile = set(self.editable_org_unit_types.exclude(id__isnull=True).values_list("id", flat=True))
        return ids_in_user_profile.union(ids_in_user_roles)

    def has_org_unit_write_permission(
        self, org_unit_type_id: int, prefetched_editable_org_unit_type_ids: set[int] = None
    ) -> bool:
        editable_org_unit_type_ids = prefetched_editable_org_unit_type_ids or self.get_editable_org_unit_type_ids()
        if not editable_org_unit_type_ids:
            return True
        return org_unit_type_id in editable_org_unit_type_ids


class ExportRequest(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")
    params = models.JSONField(null=True, blank=True)
    launcher = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    result = models.JSONField(null=True, blank=True)

    finished = models.BooleanField(default=False)

    status = models.TextField(choices=STATUS_TYPE_CHOICES, default=QUEUED)

    instance_count = models.IntegerField()
    exported_count = models.IntegerField()
    errored_count = models.IntegerField()

    last_error_message = models.TextField()
    continue_on_error = models.BooleanField(default=False)
    # user requested the export
    queued_at = models.DateTimeField(auto_now_add=True)
    # backend started processing the export
    started_at = models.DateTimeField(null=True, blank=True)
    # backend ended processing the export
    ended_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.id} ({self.status}) {self.params} {self.last_error_message} {self.launcher}"


class ExportLog(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")
    sent = models.JSONField(null=True, blank=True)
    received = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    http_status = models.IntegerField(null=True, blank=True)
    url = models.TextField(null=True, blank=True)

    def __str__(self):
        return (
            "ExportLog("
            + str(self.id)
            + "): "
            + str(self.url)
            + " got "
            + str(self.http_status)
            + " received: "
            + str(self.received)
            + " sent: "
            + str(self.sent)
        )


class ExportStatus(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")

    export_request = models.ForeignKey(ExportRequest, on_delete=models.CASCADE)
    instance = models.ForeignKey(Instance, on_delete=models.CASCADE)
    status = models.TextField(choices=STATUS_TYPE_CHOICES, default=QUEUED)
    mapping_version = models.ForeignKey(MappingVersion, on_delete=models.CASCADE)

    export_logs = models.ManyToManyField(ExportLog, blank=True)
    last_error_message = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "ExportStatus " + str(self.id)


class FeatureFlag(models.Model):
    INSTANT_EXPORT = "INSTANT_EXPORT"
    TAKE_GPS_ON_FORM = "TAKE_GPS_ON_FORM"
    REQUIRE_AUTHENTICATION = "REQUIRE_AUTHENTICATION"
    FORMS_AUTO_UPLOAD = "FORMS_AUTO_UPLOAD"
    LIMIT_OU_DOWNLOAD_TO_ROOTS = "LIMIT_OU_DOWNLOAD_TO_ROOTS"
    HOME_OFFLINE = "HOME_OFFLINE"

    FEATURE_FLAGS = {
        (INSTANT_EXPORT, "Instant export", _("Immediate export of instances to DHIS2")),
        (
            TAKE_GPS_ON_FORM,
            "Mobile: take GPS on new form",
            False,
            _("GPS localization on start of instance on mobile"),
        ),
        (
            REQUIRE_AUTHENTICATION,
            "Mobile: authentication required",
            _("Require authentication on mobile"),
        ),
        (
            LIMIT_OU_DOWNLOAD_TO_ROOTS,
            False,
            "Mobile: Limit download of orgunit to what the user has access to",
            _(
                "Mobile: Limit download of orgunit to what the user has access to",
            ),
        ),
        (
            FORMS_AUTO_UPLOAD,
            "",
            False,
            _(
                "Saving a form as finalized on mobile triggers an upload attempt immediately + everytime network becomes available"
            ),
        ),
    }

    code = models.CharField(max_length=100, null=False, blank=False, unique=True)
    name = models.CharField(max_length=100, null=False, blank=False)
    requires_authentication = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class BulkCreateUserCsvFile(models.Model):
    file = models.FileField(blank=False, null=False)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True)
    account = models.ForeignKey(Account, on_delete=models.PROTECT, null=True)


class InstanceLockQueryset(models.QuerySet):
    def actives(self):
        """Lock that don't have been unlocked"""
        return self.filter(unlocked_by__isnull=True)


class InstanceLock(models.Model):
    instance = models.ForeignKey("Instance", on_delete=models.CASCADE)
    locked_at = models.DateTimeField(auto_now_add=True)
    locked_by = models.ForeignKey(User, on_delete=models.PROTECT)
    unlocked_at = models.DateTimeField(blank=True, null=True)
    unlocked_by = models.ForeignKey(User, on_delete=models.PROTECT, blank=True, null=True, related_name="+")
    top_org_unit = models.ForeignKey("OrgUnit", on_delete=models.PROTECT, related_name="instance_lock")

    # We CASCADE if we delete the instance because the lock don't make sense then
    # but if the user or orgunit is deleted we should probably worry hence protect
    def __str__(self):
        return (
            f"{self.instance} - {self.locked_by} " + f"UNLOCKED by {self.unlocked_by}" if self.unlocked_by else "LOCKED"
        )

    class Meta:
        ordering = ["-locked_at"]


class UserRole(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    group = models.OneToOneField(auth.models.Group, on_delete=models.CASCADE, related_name="iaso_user_role")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Each user can have restricted write access to OrgUnits, based on their type.
    # By default, empty `editable_org_unit_types` means access to everything.
    editable_org_unit_types = models.ManyToManyField(
        "OrgUnitType", related_name="editable_by_user_role_set", blank=True
    )

    def __str__(self) -> str:
        return self.group.name

    def as_short_dict(self):
        return {
            "id": self.id,
            "name": self.remove_user_role_name_prefix(self.group.name),
            "group_id": self.group.id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    # This method will remove a given prefix from a string
    @staticmethod
    def remove_user_role_name_prefix(str):
        prefix = str.split("_")[0] + "_"
        if str.startswith(prefix):
            return str[len(prefix) :]
        return str

    def as_dict(self):
        return {
            "id": self.id,
            "name": self.remove_user_role_name_prefix(self.group.name),
            "group_id": self.group.id,
            "permissions": list(
                self.group.permissions.filter(codename__startswith="iaso_").values_list("codename", flat=True)
            ),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
