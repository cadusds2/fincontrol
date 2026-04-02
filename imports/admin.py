"""Admin do app imports."""

from django import forms
from django.contrib import admin
from django.contrib import messages
from django.db import transaction

from .models import ImportBatch
from .services.import_service import executar_importacao_import_batch


class FormularioImportBatchAdmin(forms.ModelForm):
    """Valida requisitos mínimos de criação do lote de importação."""

    class Meta:
        model = ImportBatch
        fields = "__all__"

    def clean(self):
        dados_limpos = super().clean()
        if not self.instance.pk and not dados_limpos.get("file"):
            raise forms.ValidationError("É obrigatório anexar um arquivo CSV para criar o lote.")
        return dados_limpos


@admin.register(ImportBatch)
class ImportBatchAdmin(admin.ModelAdmin):
    form = FormularioImportBatchAdmin
    list_display = (
        "id",
        "account",
        "reference_month",
        "file_type",
        "status",
        "rows_total",
        "rows_imported",
        "rows_skipped",
        "imported_at",
    )
    list_filter = ("file_type", "status", "imported_at", "account__bank_name")
    search_fields = ("source_filename", "account__display_name", "account__bank_name")
    autocomplete_fields = ("account",)
    readonly_fields = (
        "rows_total",
        "rows_imported",
        "rows_skipped",
        "total_rows",
        "imported_rows",
        "duplicated_rows",
        "error_log",
        "created_at",
        "updated_at",
    )
    fields = (
        "account",
        "reference_month",
        "file_type",
        "file",
        "source_filename",
        "status",
        "rows_total",
        "rows_imported",
        "rows_skipped",
        "total_rows",
        "imported_rows",
        "duplicated_rows",
        "error_log",
        "imported_at",
        "created_at",
        "updated_at",
    )
    date_hierarchy = "imported_at"
    list_select_related = ("account",)
    ordering = ("-imported_at", "-id")
    list_per_page = 50

    def save_model(self, request, obj, form, change):
        novo_lote = obj.pk is None
        super().save_model(request, obj, form, change)
        if not novo_lote:
            return

        def executar_pipeline():
            resultado = executar_importacao_import_batch(obj.id)
            mensagem = (
                f"Importação finalizada: total={resultado.linhas_total}, "
                f"importadas={resultado.linhas_importadas}, puladas={resultado.linhas_puladas}."
            )
            if resultado.total_erros:
                mensagem += " Verifique o campo error_log para detalhes."
            messages.add_message(request, messages.INFO, mensagem)

        transaction.on_commit(executar_pipeline)
