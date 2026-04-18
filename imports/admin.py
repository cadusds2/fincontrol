"""Admin do app imports."""

from django import forms
from django.contrib import admin
from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse

from .models import ImportBatch
from .services.import_service import (
    executar_importacao_em_massa,
    executar_importacao_import_batch,
)


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={"multiple": True}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        if not data:
            if self.required:
                raise forms.ValidationError(self.error_messages["required"], code="required")
            return []
        arquivos = data if isinstance(data, (list, tuple)) else [data]
        return [super(MultipleFileField, self).clean(arquivo, initial) for arquivo in arquivos]


class FormularioImportacaoEmMassaAdmin(forms.Form):
    account = forms.ModelChoiceField(
        queryset=None,
        label="Conta/cartao",
        help_text="A mesma conta/cartao sera usada para todos os arquivos.",
    )
    file_type = forms.ChoiceField(
        choices=ImportBatch.FileType.choices,
        label="Tipo de arquivo",
        help_text="O mesmo tipo sera usado para todos os arquivos. Nao ha autodeteccao no MVP.",
    )
    files = MultipleFileField(
        label="Arquivos CSV",
        help_text="Selecione um ou mais CSVs. Cada arquivo criara um ImportBatch independente.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from accounts.models import Account

        self.fields["account"].queryset = Account.objects.filter(is_active=True).order_by("display_name")


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
    change_list_template = "admin/imports/importbatch/change_list.html"
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

    def get_urls(self):
        urls = super().get_urls()
        urls_personalizadas = [
            path(
                "importacao-em-massa/",
                self.admin_site.admin_view(self.importacao_em_massa_view),
                name="imports_importbatch_importacao_em_massa",
            ),
        ]
        return urls_personalizadas + urls

    def importacao_em_massa_view(self, request):
        if request.method == "POST":
            form = FormularioImportacaoEmMassaAdmin(request.POST, request.FILES)
            if form.is_valid():
                resultado = executar_importacao_em_massa(
                    account_id=form.cleaned_data["account"].id,
                    file_type=form.cleaned_data["file_type"],
                    arquivos=form.cleaned_data["files"],
                )
                mensagem = (
                    f"Importacao em massa finalizada: arquivos={resultado.total_arquivos}, "
                    f"lotes={resultado.lotes_criados}, importadas={resultado.linhas_importadas}, "
                    f"puladas={resultado.linhas_puladas}, duplicadas={resultado.linhas_duplicadas}, "
                    f"falhas={resultado.arquivos_com_falha}."
                )
                self.message_user(request, mensagem, messages.INFO)
                if resultado.arquivos_com_falha:
                    falhas = ", ".join(
                        arquivo.nome_arquivo
                        for arquivo in resultado.arquivos
                        if arquivo.status == ImportBatch.Status.FAILED
                    )
                    self.message_user(
                        request,
                        "Arquivos com falha: " + falhas,
                        messages.WARNING,
                    )
                return redirect(reverse("admin:imports_importbatch_changelist"))
        else:
            form = FormularioImportacaoEmMassaAdmin()

        contexto = {
            **self.admin_site.each_context(request),
            "title": "Importacao em massa de CSVs",
            "opts": self.model._meta,
            "form": form,
        }
        return TemplateResponse(
            request,
            "admin/imports/importbatch/importacao_em_massa.html",
            contexto,
        )

    def save_model(self, request, obj, form, change):
        novo_lote = obj.pk is None
        super().save_model(request, obj, form, change)
        if not novo_lote:
            return

        def executar_pipeline():
            resultado = executar_importacao_import_batch(obj.id)
            mensagem = (
                f"Importacao finalizada: total={resultado.linhas_total}, "
                f"importadas={resultado.linhas_importadas}, puladas={resultado.linhas_puladas}."
            )
            if resultado.total_erros:
                mensagem += " Verifique o campo error_log para detalhes."
            messages.add_message(request, messages.INFO, mensagem)

        transaction.on_commit(executar_pipeline)
