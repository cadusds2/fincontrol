from django.contrib import admin

from transactions.models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "transaction_date",
        "account",
        "amount",
        "currency",
        "direction",
        "classification_source",
        "category",
    )
    list_filter = ("direction", "classification_source", "currency", "account")
    search_fields = ("description_raw", "description_norm", "merchant_norm", "raw_hash")
    autocomplete_fields = ("import_batch", "account", "category")
    date_hierarchy = "transaction_date"
