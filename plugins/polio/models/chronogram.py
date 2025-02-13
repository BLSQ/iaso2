from translated_fields import TranslatedField

from django.contrib.auth.models import User
from django.db import models
from django.db.models import (
    BooleanField,
    Case,
    Count,
    DateField,
    ExpressionWrapper,
    F,
    IntegerField,
    OuterRef,
    Q,
    Subquery,
    Value,
    When,
)
from django.db.models.functions import ExtractDay, Coalesce
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from iaso.models import Account
from iaso.utils.models.soft_deletable import SoftDeletableModel
from plugins.polio.models import Round


class Period(models.TextChoices):
    BEFORE = "BEFORE", _("Before")
    DURING = "DURING", _("During")
    AFTER = "AFTER", _("After")


class ChronogramQuerySet(models.QuerySet):
    def valid(self):
        return self.filter(deleted_at__isnull=True)  # Hide soft deleted items.


class ChronogramManager(models.Manager):
    def get_queryset(self):
        num_tasks_delayed = Subquery(
            ChronogramTask.objects.valid()
            .filter(chronogram=OuterRef("pk"), annotated_delay_in_days__lt=0)
            .values("chronogram")
            .annotate(count=Count("id"))
            .values("count"),
            output_field=IntegerField(),
        )
        return (
            super()
            .get_queryset()
            .annotate(
                annotated_num_task_delayed=Coalesce(num_tasks_delayed, 0),
            )
            .annotate(
                annotated_is_on_time=ExpressionWrapper(Q(annotated_num_task_delayed=0), output_field=BooleanField())
            )
        )


class Chronogram(SoftDeletableModel):
    """
    A chronogram can be thought as a to-do list.
    """

    round = models.ForeignKey(Round, on_delete=models.CASCADE, related_name="chronograms")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_chronograms"
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="updated_chronograms"
    )

    objects = ChronogramManager.from_queryset(ChronogramQuerySet)()

    class Meta:
        verbose_name = _("Chronogram")

    def __str__(self) -> str:
        return f"{self.id} - {self.round.campaign.obr_name} - Round {self.round.number}"

    @property
    def percentage_of_completion(self) -> dict:
        tasks = self.tasks.all()

        tasks_before = [t for t in tasks if t.period == Period.BEFORE]
        tasks_before_done = [t for t in tasks_before if t.status == self.tasks.model.Status.DONE]

        tasks_during = [t for t in tasks if t.period == Period.DURING]
        tasks_during_done = [t for t in tasks_during if t.status == self.tasks.model.Status.DONE]

        tasks_after = [t for t in tasks if t.period == Period.AFTER]
        tasks_after_done = [t for t in tasks_after if t.status == self.tasks.model.Status.DONE]

        return {
            Period.BEFORE.value: int(len(tasks_before_done) / len(tasks_before) * 100) if tasks_before else 0,
            Period.DURING.value: int(len(tasks_during_done) / len(tasks_during) * 100) if tasks_during else 0,
            Period.AFTER.value: int(len(tasks_after_done) / len(tasks_after) * 100) if tasks_after else 0,
        }


class ChronogramTaskQuerySet(models.QuerySet):
    def valid(self):
        return self.filter(deleted_at__isnull=True)  # Hide soft deleted items.


class ChronogramTaskManager(models.Manager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("chronogram__round")
            .annotate(
                annotated_deadline_date=ExpressionWrapper(
                    F("chronogram__round__started_at") + F("start_offset_in_days"), output_field=DateField()
                ),
                # A negative delay in days means that the task is delayed.
                annotated_delay_in_days=Case(
                    When(status=self.model.Status.DONE, then=Value(0)),
                    default=ExpressionWrapper(
                        ExtractDay(F("annotated_deadline_date") - Value(timezone.now().date())),
                        output_field=IntegerField(),
                    ),
                    output_field=IntegerField(),
                ),
            )
        )


class ChronogramTask(SoftDeletableModel):
    """
    A chronogram task can be thought as a to-do list item.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", _("Not started")
        IN_PROGRESS = "IN_PROGRESS", _("In progress")
        DONE = "DONE", _("Done")
        NA = "NON_APPLICABLE", _("N/A")

    chronogram = models.ForeignKey(Chronogram, on_delete=models.CASCADE, related_name="tasks")
    period = models.CharField(max_length=15, choices=Period.choices, default=Period.BEFORE)
    description = TranslatedField(models.TextField(max_length=300), {"fr": {"blank": True}})
    start_offset_in_days = models.IntegerField(default=0)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    user_in_charge = models.CharField(max_length=255, blank=True)
    comment = models.TextField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_chronogram_tasks"
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="updated_chronogram_tasks"
    )

    objects = ChronogramTaskManager.from_queryset(ChronogramTaskQuerySet)()

    class Meta:
        verbose_name = _("Chronogram Task")

    def __str__(self) -> str:
        return f"{self.id} - {self.status}"


class ChronogramTemplateQuerySet(models.QuerySet):
    def valid(self):
        return self.filter(deleted_at__isnull=True)  # Hide soft deleted items.


class ChronogramTemplateTaskManager(models.Manager):
    def create_chronogram(self, round: Round, created_by: User, account: Account = None) -> Chronogram:
        account_id = account.id if account else created_by.iaso_profile.account_id
        chronogram = Chronogram.objects.create(round=round, created_by=created_by)

        tasks = [
            ChronogramTask(
                chronogram=chronogram,
                created_by=created_by,
                description_en=template.description_en,
                description_fr=template.description_fr,
                period=template.period,
                start_offset_in_days=template.start_offset_in_days,
            )
            for template in self.model.objects.valid().filter(account_id=account_id)
        ]
        if tasks:
            ChronogramTask.objects.bulk_create(tasks)

        return chronogram


class ChronogramTemplateTask(SoftDeletableModel):
    """
    Template tasks used by default to create a chronogram.
    """

    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    period = models.CharField(max_length=15, choices=Period.choices, default=Period.BEFORE)
    description = TranslatedField(models.TextField(max_length=300), {"fr": {"blank": True}})
    start_offset_in_days = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_chronogram_templates"
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="updated_chronogram_templates"
    )

    objects = ChronogramTemplateTaskManager.from_queryset(ChronogramTemplateQuerySet)()

    class Meta:
        verbose_name = _("Chronogram Template Task")

    def __str__(self) -> str:
        return f"{self.id} - {self.account.name}"
