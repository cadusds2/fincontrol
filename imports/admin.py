from django.contrib import admin

from imports.models import ImportBatch


@admin.register(ImportBatch)
class ImportBatchAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "account",
        "file_type",
        "source_filename",
        "status",
        "total_rows",
        "imported_rows",
        "duplicated_rows",
        "imported_at",
    )
    list_filter = ("file_type", "status", "account")
    search_fields = ("source_filename", "error_log")
    autocomplete_fields = ("account",)
