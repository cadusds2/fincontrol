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
    )
    list_filter = ("direction", "classification_source", "currency", "transaction_date")
    search_fields = ("description_raw", "description_norm", "merchant_norm", "raw_hash")
    autocomplete_fields = ("account", "import_batch", "category")
