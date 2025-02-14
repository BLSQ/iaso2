import typing
import uuid
from typing import Optional

from django.contrib.auth.models import User, AnonymousUser
from django.db import models

from iaso.models.entity import EntityType, Form
from ..utils.models.soft_deletable import (
    SoftDeletableModel,
    DefaultSoftDeletableManager,
    OnlyDeletedSoftDeletableManager,
    IncludeDeletedSoftDeletableManager,
)


class WorkflowQuerySet(models.QuerySet):
    pass


class Workflow(SoftDeletableModel):
    """A workflow is linked one to one with a entity type.
    A workflow has versions of the type WorkflowVersion which includes the real content of the workflow."""

    entity_type = models.OneToOneField(
        EntityType,
        on_delete=models.CASCADE,
        related_name="workflow",
    )

    uuid = models.UUIDField(default=uuid.uuid4, unique=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = DefaultSoftDeletableManager.from_queryset(WorkflowQuerySet)()

    objects_only_deleted = OnlyDeletedSoftDeletableManager.from_queryset(WorkflowQuerySet)()

    objects_include_deleted = IncludeDeletedSoftDeletableManager.from_queryset(WorkflowQuerySet)()

    @property
    def latest_version(self):
        return self.workflow_versions.order_by("-created_at").first()

    def __str__(self):
        return f"Workflow for {self.entity_type.name}"


WorkflowVersionsStatusAllowedTransitions = {
    "DRAFT": {"UNPUBLISHED", "PUBLISHED"},
    "UNPUBLISHED": {"PUBLISHED"},
    "PUBLISHED": {"UNPUBLISHED"},
}


class WorkflowVersionsStatus(models.TextChoices):
    """WorkflowVersionsStatus is an Enum-like class for the Status of a workflow Version."""

    DRAFT = "DRAFT", "Draft"
    UNPUBLISHED = "UNPUBLISHED", "Unpublished"
    PUBLISHED = "PUBLISHED", "Published"


def is_transition_allowed(self: "WorkflowVersion", new_status: str):
    allowed_set: typing.Set[str] = WorkflowVersionsStatusAllowedTransitions.get(self.status, set())
    return new_status in allowed_set


class WorkflowVersionQuerySet(models.QuerySet):
    def filter_for_user(self, user: typing.Union[User, AnonymousUser, None]):
        if not user or user.is_anonymous:
            return self.none()

        queryset = self.all()

        if user and user.is_authenticated:
            queryset = queryset.filter(workflow__entity_type__account=user.iaso_profile.account)

        return queryset

    def filter_for_user_and_app_id(self, user: typing.Union[User, AnonymousUser, None], app_id: Optional[str]):
        queryset = self.filter_for_user(user)

        if app_id is not None:
            queryset = queryset.filter(workflow__entity_type__reference_form__projects__app_id=app_id)

        return queryset


class WorkflowVersion(SoftDeletableModel):
    """
    WorkflowVersion has 'workflow' foreign key to the Workflow object.
    reverse relations :
        changes -> WorkflowChange
        follow_ups -> WorkflowFollowup
    """

    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name="workflow_versions")

    uuid = models.UUIDField(default=uuid.uuid4, unique=True)

    name = models.CharField(max_length=50, default="No Name")
    status = models.CharField(
        max_length=12,
        choices=WorkflowVersionsStatus.choices,
        default=WorkflowVersionsStatus.DRAFT,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = DefaultSoftDeletableManager.from_queryset(WorkflowVersionQuerySet)()

    objects_only_deleted = OnlyDeletedSoftDeletableManager.from_queryset(WorkflowVersionQuerySet)()

    objects_include_deleted = IncludeDeletedSoftDeletableManager.from_queryset(WorkflowVersionQuerySet)()

    @property
    def reference_form(self):
        return self.workflow.entity_type.reference_form

    def transition_to_status(self, new_status_str: str, do_save=True):
        old_status_str = self.status

        if is_transition_allowed(self, new_status_str):
            self.status = new_status_str
            if do_save:
                self.save()

            if new_status_str == "PUBLISHED":
                # We passed all the other PUBLISHED -> UNPUBLISHED
                WorkflowVersion.objects.filter(workflow=self.workflow, status="PUBLISHED").update(status="UNPUBLISHED")

            return {"success": True}

        else:
            return {
                "success": False,
                "error": f"Transition from {old_status_str} to {new_status_str} is not allowed",
            }

    def __str__(self):
        status_label = self.status
        e_name = self.workflow.entity_type.name
        created_disp = self.created_at.strftime("%Y-%m-%d %H:%M:%S")
        return f"Workflow ({status_label}) ({e_name}) @ {created_disp}"


class WorkflowFollowup(models.Model):
    order = models.IntegerField(default=0)
    condition = models.JSONField(default=dict)
    forms = models.ManyToManyField(Form)

    # this actually points to a WorkflowVersion
    workflow_version = models.ForeignKey(WorkflowVersion, on_delete=models.CASCADE, related_name="follow_ups")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class WorkflowChange(models.Model):
    form = models.ForeignKey(Form, on_delete=models.CASCADE)
    mapping = models.JSONField(
        default=dict
    )  # dict objects with keys a field name from reference_form and value the target field name in form.

    # this actually points to a WorkflowVersion
    workflow_version = models.ForeignKey(WorkflowVersion, on_delete=models.CASCADE, related_name="changes")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
