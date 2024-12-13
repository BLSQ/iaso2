from django.contrib.gis import admin

from .models import APIImport


@admin.register(APIImport)
class APIImportAdmin(admin.GISModelAdmin):
    date_hierarchy = "created_at"
    search_fields = ("json_body", "headers", "exception")
    list_display = (
        "id",
        "import_type",
        "has_problem",
        "user",
    )
    list_filter = (
        "has_problem",
        "import_type",
    )

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("user")
