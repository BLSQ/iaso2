import gspread.utils  # type: ignore
from translated_fields import TranslatedFieldAdmin

from django import forms
from django.contrib import admin, messages
from django.contrib.admin import widgets
from django.db import models
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.safestring import mark_safe

from iaso.admin import IasoJSONEditorWidget
from plugins.polio.api.vaccines.supply_chain import validate_rounds_and_campaign
from plugins.polio.models.base import VaccineStockHistory

from .budget.models import BudgetProcess, BudgetStep, BudgetStepFile, BudgetStepLink, MailTemplate, WorkflowModel
from .models import (
    Campaign,
    CampaignType,
    CampaignGroup,
    Chronogram,
    ChronogramTask,
    ChronogramTemplateTask,
    CountryUsersGroup,
    DestructionReport,
    IncidentReport,
    Notification,
    NotificationImport,
    OutgoingStockMovement,
    ReasonForDelay,
    Round,
    RoundDateHistoryEntry,
    SpreadSheetImport,
    SubActivity,
    SubActivityScope,
    URLCache,
    VaccineArrivalReport,
    VaccineAuthorization,
    VaccinePreAlert,
    VaccineRequestForm,
    VaccineStock,
    EarmarkedStock,
    create_polio_notifications_async,
)


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    raw_id_fields = ("initial_org_unit",)
    formfield_overrides = {
        models.ForeignKey: {"widget": widgets.AdminTextInputWidget},
    }
    list_filter = ["virus", "detection_status", "risk_assessment_status", "budget_status", "campaign_types"]

    def save_model(self, request, obj: Campaign, form, change):
        obj.update_geojson_field()
        super().save_model(request, obj, form, change)

    @admin.action(description="Force update of geojson field")
    def force_update_campaign_shape(self, request, queryset):
        c: Campaign
        for c in queryset:
            c.update_geojson_field()
            c.save()
        self.message_user(request, f"GeoJson of {queryset.count()} campaign updated")

    actions = [force_update_campaign_shape]


@admin.register(SpreadSheetImport)
class SpreadSheetImportAdmin(admin.ModelAdmin):
    list_filter = ["spread_id", "created_at"]
    list_display = ["spread_id", "title", "created_at", "url"]
    readonly_fields = ["title", "table"]
    formfield_overrides = {models.JSONField: {"widget": IasoJSONEditorWidget}}

    def title(self, obj: SpreadSheetImport):
        return obj.content["title"]

    def table(self, obj: SpreadSheetImport):
        # Write a get-method for a list of module names in the class Profile
        # return HTML string which will be display in the form
        # for sheet in self.content['sheets']:
        html = ""

        for sheet in obj.content["sheets"]:
            html += f'<details open><summary><b>{sheet["title"]}</b></summary><table>'
            try:
                if not sheet["values"]:
                    html += "Empty</table></details>"
                    continue

                values = gspread.utils.fill_gaps(sheet["values"])

                html += "<tr><td></td>"
                for col_num in range(len(values[0])):
                    html += f"<td>{col_num}</td>"
                html += "</tr>"

                for row_num, row in enumerate(values):
                    html += f"<tr><td>{row_num}</td>"

                    for col in row:
                        html += f"<td>{col}</td>\n"
                    html += "</tr>"

            except Exception as e:
                print(e)
                html += f"<error>render error: {e}</error>"
                html += f'<pre>{sheet["values"]}</pre>'
            html += "</table></details>"

        # print(html)
        return mark_safe(html)


@admin.register(CampaignGroup)
class CampaignGroupAdmin(admin.ModelAdmin):
    pass


@admin.register(MailTemplate)
class MailTemplateAdmin(admin.ModelAdmin):
    pass


class BudgetStepLinkAdminInline(admin.TabularInline):
    model = BudgetStepLink
    extra = 0


class BudgetStepFileAdminInline(admin.TabularInline):
    model = BudgetStepFile
    extra = 0


@admin.register(BudgetStep)
class BudgetStepAdmin(admin.ModelAdmin):
    inlines = [
        BudgetStepFileAdminInline,
        BudgetStepLinkAdminInline,
    ]
    list_display = ["campaign", "transition_key", "created_by", "created_at", "deleted_at"]


@admin.register(WorkflowModel)
class WorkflowAdmin(admin.ModelAdmin):
    formfield_overrides = {models.JSONField: {"widget": IasoJSONEditorWidget}}


@admin.register(VaccineAuthorization)
class VaccineAuthorizationsAdmin(admin.ModelAdmin):
    model = VaccineAuthorization
    raw_id_fields = ("country",)


class VaccineArrivalReportAdminInline(admin.TabularInline):
    model = VaccineArrivalReport
    extra = 0


class VaccinePreAlertAdminInline(admin.TabularInline):
    model = VaccinePreAlert
    extra = 0


class VaccineRequestAdminForm(forms.ModelForm):
    class Meta:
        model = VaccineRequestForm
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        return validate_rounds_and_campaign(cleaned_data)


@admin.register(VaccineRequestForm)
class VaccineRequestFormAdmin(admin.ModelAdmin):
    model = VaccineRequestForm
    form = VaccineRequestAdminForm
    inlines = [VaccinePreAlertAdminInline, VaccineArrivalReportAdminInline]
    readonly_fields = ["created_at", "updated_at"]
    list_display = ["campaign", "get_country", "count_pre_alerts", "count_arrival_reports", "created_at"]

    def save_related(self, request, form, formsets, change):
        for formset in formsets:
            if not formset.is_valid():
                print(f"Formset errors: {formset.errors}")
            else:
                formset.save()


@admin.register(VaccineStock)
class VaccineStockAdmin(admin.ModelAdmin):
    model = VaccineStock
    raw_id_fields = ("country",)
    list_display = ["country", "vaccine"]


@admin.register(OutgoingStockMovement)
class OutgoingStockMovementAdmin(admin.ModelAdmin):
    model = OutgoingStockMovement


@admin.register(DestructionReport)
class DestructionReport(admin.ModelAdmin):
    model = DestructionReport


@admin.register(IncidentReport)
class IncidentReport(admin.ModelAdmin):
    model = IncidentReport


@admin.register(EarmarkedStock)
class EarmarkedStockAdmin(admin.ModelAdmin):
    model = EarmarkedStock


@admin.register(Round)
class RoundAdmin(admin.ModelAdmin):
    model = Round
    raw_id_fields = ("campaign",)
    list_display = ["campaign", "number"]
    list_filter = ["campaign"]


@admin.register(ReasonForDelay)
class ReasonForDelayAdmin(admin.ModelAdmin):
    model = ReasonForDelay


@admin.register(NotificationImport)
class NotificationImportAdmin(admin.ModelAdmin):
    @admin.action(description="Create notifications")
    def create_notifications(self, request, queryset) -> None:
        """
        Quick and easy way to test `create_polio_notifications_async()`.
        """
        for notification_import in queryset.filter(status=NotificationImport.Status.NEW):
            create_polio_notifications_async(pk=notification_import.pk, user=request.user)
        messages.success(
            request,
            "You've been redirected to the notifications list. "
            "Import of notifications has been scheduled and will start soon. "
            "Results will appear gradually below. "
            "Please refresh in a few seconds.",
        )
        return HttpResponseRedirect(reverse("admin:polio_notification_changelist"))

    actions = (create_notifications,)
    formfield_overrides = {models.JSONField: {"widget": IasoJSONEditorWidget}}
    list_display = ("pk", "file", "status", "created_by", "account")
    list_filter = ("status",)
    raw_id_fields = ("account", "created_by")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "epid_number",
        "get_org_unit_name",
        "site_name",
        "vdpv_category",
        "source",
        "date_of_onset",
    )
    list_filter = ("vdpv_category", "source")
    raw_id_fields = ("account", "org_unit", "created_by", "updated_by", "import_source")
    read_only_fields = ("data_source",)

    @admin.display(description="Org Unit name")
    def get_org_unit_name(self, obj):
        if obj.org_unit:
            return obj.org_unit.name
        return None

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("org_unit")


@admin.register(VaccineStockHistory)
class VaccineStockHistoryAdmin(admin.ModelAdmin):
    list_display = ("get_campaign_name", "get_round_number", "round", "get_vaccine_name", "get_country")
    # list_filter = ("get_country", "get_vaccine_name","get_campaign_name")

    @admin.display(description="Campaign name")
    def get_campaign_name(self, obj):
        if obj.round:
            return obj.round.campaign.obr_name
        return None

    @admin.display(description="Round number")
    def get_round_number(self, obj):
        if obj.round:
            return obj.round.number
        return None

    @admin.display(description="Vaccine")
    def get_vaccine_name(self, obj):
        if obj.round:
            return obj.vaccine_stock.vaccine
        return None

    @admin.display(description="Country")
    def get_country(self, obj):
        if obj.round:
            return obj.vaccine_stock.country.name
        return None

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("round", "vaccine_stock", "vaccine_stock__country")


class RoundAdminInline(admin.TabularInline):
    model = Round
    extra = 0
    show_change_link = True
    can_delete = False
    fields = ("id", "started_at", "number", "campaign")
    readonly_fields = ("id", "started_at", "number", "campaign")


class BudgetStepAdminInline(admin.TabularInline):
    model = BudgetStep
    extra = 0
    show_change_link = True
    can_delete = False
    fields = ("id", "created_at", "transition_key", "created_by")
    readonly_fields = ("id", "created_at", "transition_key", "created_by")


@admin.register(BudgetProcess)
class BudgetProcessAdmin(admin.ModelAdmin):
    raw_id_fields = ("created_by",)
    inlines = [RoundAdminInline, BudgetStepAdminInline]


class SubActivityScopeInline(admin.StackedInline):
    model = SubActivityScope
    extra = 0
    show_change_link = True
    fields = ("id", "group", "vaccine")
    raw_id_fields = ("group",)


@admin.register(SubActivity)
class SubActivityAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "start_date",
        "end_date",
    )
    fields = ("name", "start_date", "end_date", "round")
    raw_id_fields = ("round",)
    inlines = [SubActivityScopeInline]

    def save_related(self, request, form, formsets, change):
        for formset in formsets:
            if not formset.is_valid():
                print(f"Formset errors: {formset.errors}")
            else:
                if formset.extra_forms:
                    for fo in formset.extra_forms:
                        if fo.is_valid():
                            fo.save()
                        else:
                            print(f"Form errors: {fo.errors}")
                formset.save()


class ChronogramTaskAdminInline(admin.StackedInline):
    model = ChronogramTask
    extra = 0
    raw_id_fields = ("created_by", "updated_by")
    readonly_fields = (
        "created_at",
        "created_by",
        "deleted_at",
        "updated_at",
        "updated_by",
    )

    def get_queryset(self, request):
        return super().get_queryset(request).valid().select_related("chronogram__round", "created_by", "updated_by")


@admin.register(Chronogram)
class ChronogramAdmin(TranslatedFieldAdmin, admin.ModelAdmin):
    date_hierarchy = "created_at"
    list_display = ("pk", "obr_name", "created_at")
    list_display_links = ("pk", "obr_name")
    inlines = [ChronogramTaskAdminInline]
    raw_id_fields = ("round", "created_by", "updated_by")
    readonly_fields = (
        "created_at",
        "created_by",
        "deleted_at",
        "updated_at",
        "updated_by",
    )
    search_fields = ("pk", "round__campaign__obr_name")

    @admin.display(empty_value="")
    def obr_name(self, obj):
        return obj.round.campaign.obr_name

    def get_queryset(self, request):
        return super().get_queryset(request).valid().select_related("round__campaign", "created_by", "updated_by")

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        else:
            obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ChronogramTemplateTask)
class ChronogramTemplateTaskAdmin(TranslatedFieldAdmin, admin.ModelAdmin):
    date_hierarchy = "created_at"
    list_display = ("pk", "start_offset_in_days", "description", "created_at")
    list_display_links = ("pk", "start_offset_in_days", "description")
    list_filter = ("account__name",)
    raw_id_fields = ("account", "created_by", "updated_by")
    readonly_fields = (
        "created_at",
        "created_by",
        "deleted_at",
        "updated_at",
        "updated_by",
    )
    search_fields = ("pk", "account__name")

    def get_queryset(self, request):
        return super().get_queryset(request).valid().select_related("account", "created_by", "updated_by")

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        else:
            obj.updated_by = request.user
        super().save_model(request, obj, form, change)


admin.site.register(RoundDateHistoryEntry)
admin.site.register(CountryUsersGroup)
admin.site.register(URLCache)
admin.site.register(CampaignType)
