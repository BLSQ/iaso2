from django.contrib import admin
from .models import Import, ActivePatientsList, Validation, Month


@admin.register(Import)
class ImportAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "org_unit",
        "month",
        "creation_date",
        "source",
        "hash_key",
        "file_name",
        "file_check",
    )
    list_filter = ("source", "month", "creation_date")
    search_fields = ("file_name", "hash_key")
    raw_id_fields = ("org_unit",)


@admin.register(ActivePatientsList)
class ActivePatientsListAdmin(admin.ModelAdmin):
    list_display = (
        "number",
        "region",
        "district",
        "code_ets",
        "facility_name",
        "period",
        "identifier_code",
        "sex",
        "age",
        "new_inclusion",
        "transfer_in",
        "active",
        "validation_status",
    )
    list_filter = (
        "sex",
        "region",
        "district",
        "period",
        "new_inclusion",
        "transfer_in",
        "active",
        "validation_status",
        "hiv_type",
        "treatment_line",
    )
    search_fields = ("code_ets", "facility_name", "region", "district")
    raw_id_fields = ("import_source", "org_unit")  # For faster searching in large datasets


@admin.register(Validation)
class ValidationAdmin(admin.ModelAdmin):
    list_display = (
        "source_import",
        "created_at",
        "user_name",
        "level",
        "comment",
        "validation_status",
    )
    list_filter = ("level", "validation_status", "created_at")
    search_fields = ("user_name", "comment")
    raw_id_fields = ("source_import",)


@admin.register(Month)
class MonthAdmin(admin.ModelAdmin):
    list_display = ("value",)
