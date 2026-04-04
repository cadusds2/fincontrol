"""Admin do app transactions."""

from django.contrib import admin
from django.db.models import QuerySet

from .models import Transaction


class FiltroStatusClassificacao(admin.SimpleListFilter):
    title = "status de classificação"
    parameter_name = "status_classificacao"

    def lookups(self, request, model_admin):
        return (
            ("classificadas", "Classificadas"),
            ("nao_classificadas", "Não classificadas"),
            ("manuais", "Classificação manual"),
        )

    def queryset(self, request, queryset: QuerySet[Transaction]):
        valor = self.value()
        if valor == "classificadas":
            return queryset.exclude(category__isnull=True)
        if valor == "nao_classificadas":
            return queryset.filter(category__isnull=True)
        if valor == "manuais":
            return queryset.filter(classification_source=Transaction.ClassificationSource.MANUAL)
        return queryset


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
        "classification_confidence",
        "merchant_norm",
        "import_batch",
    )
    list_filter = (
        FiltroStatusClassificacao,
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
        "merchant_raw",
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
