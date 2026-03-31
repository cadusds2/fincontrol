"""Admin do app imports."""

from django.contrib import admin

from .models import ImportBatch


@admin.register(ImportBatch)
class ImportBatchAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "account",
        "file_type",
        "status",
        "total_rows",
        "imported_rows",
        "duplicated_rows",
        "imported_at",
    )
    list_filter = ("file_type", "status", "imported_at")
    search_fields = ("source_filename", "account__display_name", "account__bank_name")
