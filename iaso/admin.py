from typing import Any, Protocol

from django import forms as django_forms
from django.contrib import admin
from django.contrib.admin import widgets, SimpleListFilter
from django.contrib.gis import admin, forms
from django.contrib.gis.db import models as geomodels
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe
from django_json_widget.widgets import JSONEditorWidget

from hat.audit.models import DJANGO_ADMIN
from iaso.models.json_config import Config  # type: ignore
from iaso.utils.admin.custom_filters import (
    DuplicateUUIDFilter,
    EntityEmptyAttributesFilter,
    has_relation_filter_factory,
)

from .models import (
    Account,
    AccountFeatureFlag,
    AlgorithmRun,
    BulkCreateUserCsvFile,
    DataSource,
    Device,
    DeviceOwnership,
    DevicePosition,
    Entity,
    EntityDuplicate,
    EntityDuplicateAnalyzis,
    EntityType,
    ExportLog,
    ExportRequest,
    ExportStatus,
    ExternalCredentials,
    FeatureFlag,
    Form,
    FormAttachment,
    FormPredefinedFilter,
    FormVersion,
    Group,
    GroupSet,
    Instance,
    InstanceFile,
    InstanceLock,
    Link,
    Mapping,
    MappingVersion,
    MatchingAlgorithm,
    OrgUnit,
    OrgUnitChangeRequest,
    OrgUnitChangeRequestConfiguration,
    OrgUnitReferenceInstance,
    OrgUnitType,
    Page,
    Payment,
    PaymentLot,
    PotentialPayment,
    Profile,
    Project,
    Report,
    ReportVersion,
    SourceVersion,
    StorageDevice,
    StorageLogEntry,
    StoragePassword,
    Task,
    TenantUser,
    UserRole,
    Workflow,
    WorkflowChange,
    WorkflowFollowup,
    WorkflowVersion,
)
from .models.data_store import JsonDataStore
from .models.microplanning import Assignment, Planning, Team
from .utils.gis import convert_2d_point_to_3d


class EntityAutocompleteFilter(SimpleListFilter):
    """
    Limit `entity` list_filter to only entities linked to at least one storage device.
    """

    title = "entity"
    parameter_name = "entity"

    def lookups(self, request, model_admin):
        lookups = []
        storage_device_ids = set(StorageDevice.objects.values_list("entity_id", flat=True))
        entities = Entity.objects.filter(id__in=storage_device_ids).only("pk", "name")
        for entity in entities:
            lookups.append([entity.pk, entity.name])
        return lookups

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(entity__id=self.value())
        return queryset


class IasoJSONEditorWidget(JSONEditorWidget):
    class Media:
        css = {"all": ("css/admin-json-widget.css",)}

    def __init__(self, attrs=None, mode="code", options=None, width=None, height=None):
        if height == None:
            height = "400px"

        default_options = {
            "modes": ["text", "code"],
            "mode": mode,
            "search": True,
        }
        if options:
            default_options.update(options)

        super().__init__(attrs=attrs, mode=mode, options=default_options, width=width, height=height)


class ArrayFieldMultipleChoiceField(django_forms.MultipleChoiceField):
    """
    Display a multi-select field for ArrayField:

    formfield_overrides = {
        ArrayField: {
            "form_class": ArrayFieldMultipleChoiceField,
        }
    }

    formfield_overrides = {
        ArrayField: {
            "form_class": ArrayFieldMultipleChoiceField,
            "widget": forms.CheckboxSelectMultiple,
        }
    }
    """

    def __init__(self, *args, **kwargs):
        kwargs.pop("max_length", None)
        base_field = kwargs.pop("base_field", None)
        kwargs["choices"] = base_field.choices
        kwargs["choices"].pop(0)
        super().__init__(*args, **kwargs)


class AdminAttributes(Protocol):
    """Workaround to avoid mypy errors, see https://github.com/python/mypy/issues/2087#issuecomment-462726600"""

    short_description: str
    admin_order_field: str


def admin_attr_decorator(func: Any) -> AdminAttributes:
    return func


class OrgUnitReferenceInstanceInline(admin.TabularInline):
    model = OrgUnitReferenceInstance
    extra = 0
    raw_id_fields = (
        "form",
        "instance",
    )
    can_delete = True

    def has_add_permission(self, request, obj=None):
        return True


@admin.register(OrgUnit)
@admin_attr_decorator
class OrgUnitAdmin(admin.GISModelAdmin):
    raw_id_fields = ("parent", "reference_instances", "default_image")
    list_filter = ("org_unit_type", "custom", "validated", "sub_source", "version")
    search_fields = ("name", "source_ref", "uuid")
    readonly_fields = ("path",)
    inlines = [
        OrgUnitReferenceInstanceInline,
    ]
    list_display = (
        "id",
        "org_unit_type",
        "name",
        "uuid",
        "parent",
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.prefetch_related("org_unit_type", "parent__org_unit_type")
        return queryset


@admin.register(OrgUnitType)
@admin_attr_decorator
class OrgUnitTypeAdmin(admin.GISModelAdmin):
    search_fields = ("name",)
    list_display = ("name", "projects_list", "short_name", "depth")
    list_filter = ("projects",)

    @admin.display(description="Projects")
    @admin_attr_decorator
    def projects_list(self, obj):
        projects = obj.projects.all()
        return ", ".join(project.name for project in projects) if len(projects) > 0 else "-"


@admin.register(Form)
@admin_attr_decorator
class FormAdmin(admin.GISModelAdmin):
    search_fields = ("name", "form_id")
    list_display = (
        "name",
        "form_id",
        "period_type",
        "single_per_period",
        "periods_before_allowed",
        "periods_after_allowed",
        "derived",
        "created_at",
        "updated_at",
        "deleted_at",
    )

    formfield_overrides = {models.JSONField: {"widget": IasoJSONEditorWidget}}

    list_filter = ["projects__account"]

    def get_queryset(self, request):
        return Form.objects_include_deleted.all()


@admin.register(FormVersion)
@admin_attr_decorator
class FormVersionAdmin(admin.GISModelAdmin):
    search_fields = ("form__name", "form__form_id")
    ordering = ("form__name",)
    list_display = ("form_name", "form_id", "version_id", "created_at", "updated_at")

    formfield_overrides = {models.JSONField: {"widget": IasoJSONEditorWidget}}

    @admin.display(
        description="Form name",
        ordering="form__name",
    )
    @admin_attr_decorator
    def form_name(self, obj):
        return obj.form.name

    @admin.display(
        description="Form ID",
        ordering="form__id",
    )
    @admin_attr_decorator
    def form_id(self, obj):
        return obj.form.form_id


@admin.register(FormPredefinedFilter)
class FormPredefinedFilterAdmin(admin.ModelAdmin):
    readonly_fields = ("created_at", "updated_at")
    list_display = ("form", "name", "short_name", "json_logic")
    list_filter = ("form", "name", "short_name")


@admin.register(FormAttachment)
class FormAttachmentAdmin(admin.ModelAdmin):
    readonly_fields = ("created_at", "updated_at")
    list_display = ("form", "name", "file", "md5")
    list_filter = ("form", "name")


class InstanceFileAdminInline(admin.TabularInline):
    model = InstanceFile
    extra = 0
    formfield_overrides = {
        models.TextField: {"widget": widgets.AdminTextInputWidget},
        models.JSONField: {"widget": IasoJSONEditorWidget},
    }


@admin.register(Instance)
@admin_attr_decorator
class InstanceAdmin(admin.GISModelAdmin):
    raw_id_fields = (
        "org_unit",
        "entity",
        "form_version",
        "last_modified_by",
        "created_by",
    )
    search_fields = ("file_name", "uuid")
    list_display = (
        "id",
        "uuid",
        "project",
        "form",
        "org_unit",
        "period",
        "created_at",
        "entity",
        "deleted",
    )
    list_filter = (
        "project",
        "form",
        "deleted",
        DuplicateUUIDFilter,
        has_relation_filter_factory("Entity ID", "entity_id"),
    )
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "deleted",
                    "form",
                    "period",
                    "uuid",
                    "name",
                    "org_unit",
                    "device",
                    "entity",
                    "last_modified_by",
                    "created_by",
                    "form_version",
                    "planning",
                )
            },
        ),
        (
            "File",
            {
                "fields": (
                    "file",
                    "file_name",
                    "correlation_id",
                    "json",
                )
            },
        ),
        ("Export", {"fields": ("to_export", "export_id", "last_export_success_at")}),
        ("Other", {"fields": ("project", "location", "accuracy")}),
    )

    formfield_overrides = {
        models.TextField: {"widget": widgets.AdminTextInputWidget},
        geomodels.PointField: {"widget": forms.OSMWidget},  # type: ignore
        models.JSONField: {"widget": IasoJSONEditorWidget},
    }
    inlines = [
        InstanceFileAdminInline,
    ]

    def save_model(self, request, obj, form, change):
        if obj.location:  # GeoDjango's map return a 2D point, but the database expect a Z value
            obj.location = convert_2d_point_to_3d(obj.location)

        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.prefetch_related(
            "org_unit__org_unit_type",
            "project",
            "form",
            "entity",
        )
        return queryset

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "entity":
            kwargs["queryset"] = (
                Entity.objects_include_deleted.all()
            )  # use the manager that includes soft-deleted objects
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(InstanceFile)
@admin_attr_decorator
class InstanceFileAdmin(admin.GISModelAdmin):
    raw_id_fields = ("instance",)
    search_fields = ("name", "file")


@admin.register(Project)
@admin_attr_decorator
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "app_id", "account", "needs_authentication", "feature_flags_list")
    autocomplete_fields = ["account"]
    search_fields = ["name"]

    @admin.display(description="Feature flags")
    @admin_attr_decorator
    def feature_flags_list(self, obj):
        flags = obj.feature_flags.all()
        return ", ".join(flag.name for flag in flags) if len(flags) > 0 else "-"


@admin.register(FeatureFlag)
@admin_attr_decorator
class FeatureFlagAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "requires_authentication")


@admin.register(Link)
@admin_attr_decorator
class LinkAdmin(admin.GISModelAdmin):
    raw_id_fields = ("source", "destination")


@admin.register(Mapping)
@admin_attr_decorator
class MappingAdmin(admin.GISModelAdmin):
    list_filter = ("form_id",)
    autocomplete_fields = ["data_source"]


@admin.register(MappingVersion)
@admin_attr_decorator
class MappingVersionAdmin(admin.GISModelAdmin):
    list_filter = ("form_version_id",)
    formfield_overrides = {models.JSONField: {"widget": IasoJSONEditorWidget}}


@admin.register(Group)
@admin_attr_decorator
class GroupAdmin(admin.ModelAdmin):
    raw_id_fields = ("org_units",)
    search_fields = ("name", "source_version", "domain")
    list_display = ("name", "source_version", "created_at", "org_unit_count", "domain", "source_ref")

    def org_unit_count(self, obj):
        return obj.org_units.count()


@admin_attr_decorator
class UserAdmin(admin.GISModelAdmin):
    search_fields = ("username", "email", "first_name", "last_name", "iaso_profile__account__name")
    list_filter = ("iaso_profile__account", "is_staff", "is_superuser", "is_active")
    list_display = ("id", "username", "email", "first_name", "last_name", "iaso_profile", "is_superuser")


@admin.register(Profile)
@admin_attr_decorator
class ProfileAdmin(admin.GISModelAdmin):
    raw_id_fields = ("org_units",)
    search_fields = ("user__username", "user__first_name", "user__last_name", "account__name")
    list_select_related = ("user", "account")
    list_filter = ("account",)
    list_display = ("id", "user", "account", "language")
    autocomplete_fields = ["account"]


@admin.register(ExportRequest)
@admin_attr_decorator
class ExportRequestAdmin(admin.GISModelAdmin):
    list_filter = ("launcher", "status")
    list_display = ("status", "launcher", "params", "last_error_message")
    readonly_fields = list_display


@admin.register(ExportLog)
@admin_attr_decorator
class ExportLogAdmin(admin.GISModelAdmin):
    list_display = ("id", "http_status", "url", "sent", "received")
    readonly_fields = list_display


@admin.register(ExportStatus)
@admin_attr_decorator
class ExportStatusAdmin(admin.GISModelAdmin):
    list_display = ("id", "status", "last_error_message")
    readonly_fields = (
        "id",
        "status",
        "last_error_message",
        "export_request",
        "instance",
        "mapping_version",
        "http_requests",
    )
    list_filter = ("status",)
    exclude = ("export_logs",)

    def http_requests(self, instance):
        # Write a get-method for a list of module names in the class Profile
        # return HTML string which will be display in the form
        return format_html_join(
            mark_safe("<br/><br/>"),
            "{} http status: {} url : {} <br/> <ul> <li>sent <pre>{}</pre> </li><li>received <pre>{}</pre></li></ul>",
            ((line.id, line.http_status, line.url, line.sent, line.received) for line in instance.export_logs.all()),
        ) or mark_safe("<span>no logs available.</span>")


@admin.register(Task)
@admin_attr_decorator
class TaskAdmin(admin.ModelAdmin):
    list_display = ("name", "account", "status", "created_at", "launcher", "result_message")
    list_filter = ("account", "status", "name")
    readonly_fields = ("stacktrace", "created_at", "result")
    formfield_overrides = {models.JSONField: {"widget": IasoJSONEditorWidget}}

    def result_message(self, task):
        return task.result and task.result.get("message", "")

    def stacktrace(self, task):
        if not task.result:
            return
        stack = task.result.get("stack_trace")
        return format_html("<p>{}</p><pre>{}</pre>", task.result.get("message", ""), stack)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("launcher")


@admin.register(SourceVersion)
@admin_attr_decorator
class SourceVersionAdmin(admin.ModelAdmin):
    readonly_fields = ("created_at",)
    list_display = ["__str__", "data_source", "number", "created_at", "updated_at"]
    list_filter = ["data_source", "created_at", "updated_at"]
    search_fields = ["data_source__name", "number", "description"]
    autocomplete_fields = ["data_source"]
    date_hierarchy = "created_at"


@admin.register(Entity)
@admin_attr_decorator
class EntityAdmin(admin.ModelAdmin):
    search_fields = [
        "uuid",
        "account__name",
        "entity_type__name",
        "attributes__json",
        "attributes__id",
        "attributes__uuid",
    ]

    def get_form(self, request, obj=None, **kwargs):
        # In the <select> for the entity type, we also want to indicate the account name
        form = super().get_form(request, obj, **kwargs)
        form.base_fields["entity_type"].label_from_instance = (
            lambda entity: f"{entity.name} (Account: {entity.account.name})"
        )
        return form

    readonly_fields = ("created_at",)
    list_display = (
        "id",
        "uuid",
        "entity_type",
        "name",
        "account",
        "deleted_at",
        "merged_to",
    )
    list_filter = (
        "account",
        "entity_type",
        "deleted_at",
        has_relation_filter_factory("Attributes ID", "attributes_id"),
        EntityEmptyAttributesFilter,
        DuplicateUUIDFilter,
    )
    raw_id_fields = ("attributes", "merged_to")

    def get_queryset(self, request):
        return Entity.objects_include_deleted.all()

    # Don't allow delete multiple to avoid deletes without side-effects and audit log
    def get_actions(self, request):
        actions = super().get_actions(request)
        if "delete_selected" in actions:
            del actions["delete_selected"]
        return actions

    # Override the Django admin delete action to do a proper soft-deletion
    def delete_view(self, request, object_id, extra_context=None):
        entity = Entity.objects_include_deleted.get(pk=object_id)

        entity.soft_delete_with_instances_and_pending_duplicates(
            audit_source=DJANGO_ADMIN,
            user=request.user,
        )

        msg = f"Entity {entity.uuid} was soft deleted, along with its instances and pending duplicates"
        self.message_user(request, msg)

        # redirect to the list view
        return HttpResponseRedirect(reverse("admin:iaso_entity_changelist"))


@admin.register(JsonDataStore)
@admin_attr_decorator
class JsonDataStoreAdmin(admin.ModelAdmin):
    raw_id_fields = ["account", "org_unit"]
    formfield_overrides = {models.JSONField: {"widget": IasoJSONEditorWidget}}


@admin.register(EntityType)
@admin_attr_decorator
class EntityTypeAdmin(admin.ModelAdmin):
    readonly_fields = ("created_at",)
    list_display = (
        "id",
        "name",
        "account",
    )


@admin.register(Planning)
@admin_attr_decorator
class PlanningAdmin(admin.ModelAdmin):
    raw_id_fields = ("org_unit",)
    list_display = (
        "id",
        "name",
        "description",
        "project",
        "org_unit",
        # "forms",
        "team",
    )
    list_filter = ("project",)
    date_hierarchy = "started_at"

    fieldsets = [
        (
            None,
            {
                "fields": (
                    "name",
                    "description",
                    "project",
                    "forms",
                    "org_unit",
                    "team",
                    "started_at",
                    "ended_at",
                ),
            },
        ),
        (
            "update info",
            {
                "fields": (
                    "created_at",
                    "created_by",
                    "updated_at",
                    "deleted_at",
                )
            },
        ),
    ]
    readonly_fields = ("updated_at", "created_at")


@admin.register(Team)
@admin_attr_decorator
class TeamAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "description",
        "project",
        "type",
        "updated_at",
        "parent",
    )
    list_filter = ("project", "type")
    date_hierarchy = "created_at"
    readonly_fields = ("path",)


@admin.register(Assignment)
@admin_attr_decorator
class AssignmentAdmin(admin.ModelAdmin):
    raw_id_fields = ("org_unit",)
    list_display = (
        "id",
        "planning",
    )
    list_filter = ("planning",)
    date_hierarchy = "created_at"


@admin.register(InstanceLock)
class InstanceLockAdmin(admin.ModelAdmin):
    raw_id_fields = ("top_org_unit",)
    list_display = ("instance", "locked_by", "top_org_unit", "locked_at", "unlocked_by", "unlocked_at")
    date_hierarchy = "locked_at"


class StorageLogEntryInline(admin.TabularInline):
    model = StorageLogEntry
    raw_id_fields = ("entity", "instances", "org_unit", "performed_by")


@admin.register(StorageDevice)
class StorageDeviceAdmin(admin.ModelAdmin):
    fields = (
        "account",
        "customer_chosen_id",
        "type",
        "status",
        "status_reason",
        "status_comment",
        "status_updated_at",
        "org_unit",
        "entity",
        "created_at",
        "updated_at",
    )
    readonly_fields = ("created_at", "updated_at", "status_updated_at")
    list_display = ("account", "type", "customer_chosen_id", "entity")
    list_filter = ("account", "type", "status", EntityAutocompleteFilter)
    raw_id_fields = ("org_unit",)
    autocomplete_fields = ["entity"]
    inlines = [
        StorageLogEntryInline,
    ]


@admin.register(StoragePassword)
class StoragePasswordAdmin(admin.ModelAdmin):
    fields = (
        "password",
        "is_compromised",
        "project",
        "created_at",
        "updated_at",
    )
    readonly_fields = ("created_at", "updated_at")
    list_display = ("project", "password")
    list_filter = ("project", "is_compromised")


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    readonly_fields = ("created_at", "updated_at")

    def get_form(self, request, obj=None, **kwargs):
        # In the <select> for the entity type, we also want to indicate the account name
        form = super().get_form(request, obj, **kwargs)
        form.base_fields["entity_type"].label_from_instance = (
            lambda entity: f"{entity.name} (Account: {entity.account.name})"
        )
        return form

    def get_queryset(self, request):
        return Workflow.objects_include_deleted.all()


class WorkflowChangeInline(admin.TabularInline):
    model = WorkflowChange
    formfield_overrides = {models.JSONField: {"widget": IasoJSONEditorWidget}}


class WorkflowFollowupInline(admin.TabularInline):
    model = WorkflowFollowup
    formfield_overrides = {models.JSONField: {"widget": IasoJSONEditorWidget}}


@admin.register(WorkflowVersion)
class WorkflowVersionAdmin(admin.ModelAdmin):
    readonly_fields = ("created_at", "updated_at")
    inlines = [WorkflowChangeInline, WorkflowFollowupInline]
    list_filter = ("workflow", "status")

    def get_queryset(self, request):
        return WorkflowVersion.objects_include_deleted.all()


@admin.register(AlgorithmRun)
class AlgorithmRunAdmin(admin.ModelAdmin):
    formfield_overrides = {models.JSONField: {"widget": IasoJSONEditorWidget}}


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    formfield_overrides = {models.JSONField: {"widget": IasoJSONEditorWidget}}
    autocomplete_fields = ["account"]


@admin.register(EntityDuplicate)
class EntityDuplicateAdmin(admin.ModelAdmin):
    formfield_overrides = {models.JSONField: {"widget": IasoJSONEditorWidget}}

    @admin_attr_decorator
    def entity1_desc(self, obj):
        return f"{obj.entity1.name} ({obj.entity1.id})"

    @admin_attr_decorator
    def entity2_desc(self, obj):
        return f"{obj.entity2.name} ({obj.entity2.id})"

    list_display = (
        "similarity_score",
        "validation_status",
        "get_entity_type",
        "entity1_desc",
        "entity2_desc",
        "created_at",
    )
    list_filter = ("validation_status", "entity1__entity_type")


@admin.register(EntityDuplicateAnalyzis)
class EntityDuplicateAnalyzisAdmin(admin.ModelAdmin):
    formfield_overrides = {models.JSONField: {"widget": IasoJSONEditorWidget}}


@admin.register(OrgUnitChangeRequest)
class OrgUnitChangeRequestAdmin(admin.ModelAdmin):
    list_display = ("pk", "org_unit", "created_at", "status")
    list_display_links = ("pk", "org_unit")
    list_filter = ("status", "kind")
    readonly_fields = (
        "uuid",
        "created_at",
        "created_by",
        "updated_at",
        "updated_by",
        "old_parent",
        "old_name",
        "old_org_unit_type",
        "old_groups",
        "old_location",
        "old_reference_instances",
        "old_opening_date",
        "old_closed_date",
        "potential_payment",
    )
    raw_id_fields = (
        "org_unit",
        "new_parent",
        "new_org_unit_type",
        "new_groups",
        "new_reference_instances",
        "payment",
        "potential_payment",
    )
    fieldsets = (
        (
            "Informations",
            {
                "fields": (
                    "uuid",
                    "org_unit",
                    "status",
                    "payment",
                    "potential_payment",
                )
            },
        ),
        (
            "Proposed changes",
            {
                "fields": (
                    "new_parent",
                    "new_name",
                    "new_org_unit_type",
                    "new_groups",
                    "new_location",
                    "new_location_accuracy",
                    "new_reference_instances",
                    "new_opening_date",
                    "new_closed_date",
                )
            },
        ),
        (
            "Changes",
            {
                "fields": (
                    "requested_fields",
                    "approved_fields",
                )
            },
        ),
        (
            "Metadata",
            {
                "fields": (
                    "kind",
                    "created_at",
                    "created_by",
                    "updated_at",
                    "updated_by",
                    "rejection_comment",
                )
            },
        ),
        (
            "Old values",
            {
                "fields": (
                    "old_parent",
                    "old_name",
                    "old_org_unit_type",
                    "old_groups",
                    "old_location",
                    "old_reference_instances",
                    "old_opening_date",
                    "old_closed_date",
                )
            },
        ),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("org_unit__org_unit_type")


@admin.register(Config)
class ConfigAdmin(admin.ModelAdmin):
    raw_id_fields = ["users"]
    formfield_overrides = {models.JSONField: {"widget": IasoJSONEditorWidget}}


@admin.register(PotentialPayment)
class PotentialPaymentAdmin(admin.ModelAdmin):
    formfield_overrides = {models.JSONField: {"widget": IasoJSONEditorWidget}}
    list_display = ("id", "change_request_ids", "user")

    @admin.display(description="Change Request IDs")
    def change_request_ids(self, obj):
        change_requests = obj.change_requests.all()
        if change_requests:
            return format_html(
                ", ".join(
                    f'<a href="/admin/iaso/orgunitchangerequest/{cr.id}/change/">{cr.id}</a>' for cr in change_requests
                )
            )
        return "-"


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    formfield_overrides = {models.JSONField: {"widget": IasoJSONEditorWidget}}
    list_display = ("id", "status", "created_at", "updated_at", "change_request_ids")

    @admin.display(description="Change Request IDs")
    def change_request_ids(self, obj):
        change_requests = obj.change_requests.all()
        if change_requests:
            return format_html(
                ", ".join(
                    f'<a href="/admin/iaso/orgunitchangerequest/{cr.id}/change/">{cr.id}</a>' for cr in change_requests
                )
            )
        return "-"


@admin.register(PaymentLot)
class PaymentLotAdmin(admin.ModelAdmin):
    formfield_overrides = {models.JSONField: {"widget": IasoJSONEditorWidget}}
    list_display = ("id", "status", "created_at", "updated_at", "payment_ids")

    @admin.display(description="Payment IDs")
    def payment_ids(self, obj):
        payments = obj.payments.all()
        if payments:
            return format_html(
                ", ".join(
                    f'<a href="/admin/iaso/payment/{payment.id}/change/">{payment.id}</a>' for payment in payments
                )
            )
        return "-"


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    formfield_overrides = {
        ArrayField: {
            "form_class": ArrayFieldMultipleChoiceField,
            "widget": forms.CheckboxSelectMultiple,
        }
    }
    list_display = ["name", "description", "created_at", "updated_at"]
    list_filter = ["created_at", "updated_at", "public"]
    search_fields = ["name", "description"]
    date_hierarchy = "created_at"


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    search_fields = ["name", "id"]
    list_display = ["name", "created_at", "updated_at"]
    autocomplete_fields = ["default_version"]


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    autocomplete_fields = ["account"]


@admin.register(OrgUnitChangeRequestConfiguration)
class OrgUnitChangeRequestConfigurationAdmin(admin.ModelAdmin):
    autocomplete_fields = ["project"]


@admin.register(GroupSet)
class GroupSetAdmin(admin.ModelAdmin):
    autocomplete_fields = ["source_version"]


@admin.register(TenantUser)
class TenantUserAdmin(admin.ModelAdmin):
    list_display = (
        "main_user",
        "account_user",
        "account",
        "created_at",
        "updated_at",
        "all_accounts_count",
        "is_self_account",
    )
    list_filter = ("account_user__iaso_profile__account",)
    search_fields = ("main_user__username", "account_user__username", "account_user__iaso_profile__account__name")
    raw_id_fields = ("main_user", "account_user")
    readonly_fields = ("created_at", "updated_at", "account", "all_account_users", "other_accounts")

    def get_urls(self):
        urls = super().get_urls()
        return urls

    @admin.display(
        description="Account",
        ordering="account_user__iaso_profile__account",
    )
    def account(self, obj):
        return obj.account

    @admin.display(description="Total Accounts")
    def all_accounts_count(self, obj):
        return obj.main_user.tenant_users.count()

    @admin.display(
        description="Self Account",
        boolean=True,
    )
    def is_self_account(self, obj):
        return obj.main_user == obj.account_user

    @admin.display(description="All Account Users")
    def all_account_users(self, obj):
        users = obj.get_all_account_users()
        return format_html("<br>".join(user.username for user in users))

    @admin.display(description="Other Accounts")
    def other_accounts(self, obj):
        accounts = obj.get_other_accounts()
        return format_html("<br>".join(str(account) for account in accounts))

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("main_user", "account_user__iaso_profile__account")

    class Media:
        js = ("admin/js/vendor/select2/select2.full.min.js", "admin/js/autocomplete.js")
        css = {
            "all": ("admin/css/vendor/select2/select2.min.css",),
        }


admin.site.register(AccountFeatureFlag)
admin.site.register(Device)
admin.site.register(DeviceOwnership)
admin.site.register(MatchingAlgorithm)
admin.site.register(ExternalCredentials)
admin.site.register(DevicePosition)
admin.site.register(BulkCreateUserCsvFile)
admin.site.register(Report)
admin.site.register(ReportVersion)
