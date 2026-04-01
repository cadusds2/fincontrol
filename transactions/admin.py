"""Admin do app transactions."""

from django.contrib import admin

from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "transaction_date",
        "account",
        "amount",
        "direction",
        "category",
        "classification_source",
        "import_batch",
    )
    list_filter = (
        "direction",
        "classification_source",
        "currency",
        "transaction_date",
        "account__bank_name",
        "category__kind",
    )
    search_fields = (
        "description_raw",
        "description_norm",
        "merchant_norm",
        "raw_hash",
        "account__display_name",
        "import_batch__source_filename",
    )
    autocomplete_fields = ("account", "import_batch", "category")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "transaction_date"
    list_select_related = ("account", "import_batch", "category")
    ordering = ("-transaction_date", "-id")
    list_per_page = 100
