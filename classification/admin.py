"""Admin do app classification."""

from django import forms
from django.contrib import admin, messages
from django.db.models import QuerySet
from django.utils import timezone
from django.utils.html import format_html
from django.utils.text import Truncator

from .models import Category, MerchantMap, ReviewQueue
from .services.manual_review_service import revisar_transacao_manualmente


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "kind", "is_reportable", "is_active", "updated_at")
    list_filter = ("kind", "is_reportable", "is_active")
    search_fields = ("name", "slug", "description")
    ordering = ("name",)
    readonly_fields = ("created_at", "updated_at")
    list_per_page = 50


@admin.register(MerchantMap)
class MerchantMapAdmin(admin.ModelAdmin):
    list_display = (
        "merchant_norm",
        "category",
        "source",
        "confidence",
        "usage_count",
        "last_used_at",
    )
    list_filter = ("source", "category", "category__kind")
    search_fields = ("merchant_norm", "category__name")
    autocomplete_fields = ("category",)
    list_select_related = ("category",)
    list_editable = ("category", "source", "confidence")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("merchant_norm",)
    list_per_page = 100


@admin.register(ReviewQueue)
class ReviewQueueAdmin(admin.ModelAdmin):
    class FormularioRevisaoQueue(forms.ModelForm):
        categoria_final = forms.ModelChoiceField(
            queryset=Category.objects.filter(is_active=True).order_by("name"),
            required=False,
            label="Categoria final da revisão",
            help_text="Ao preencher, aplica revisão manual na transação vinculada.",
        )
        criar_merchant_map = forms.BooleanField(
            required=False,
            initial=False,
            label="Criar MerchantMap com base no merchant_norm",
        )

        class Meta:
            model = ReviewQueue
            fields = (
                "status",
                "reason",
                "suggested_category",
                "resolution_note",
            )

    form = FormularioRevisaoQueue
    actions = ("marcar_como_ignorada", "criar_merchant_map_para_selecionadas")
    list_display = (
        "id",
        "transaction",
        "data_transacao",
        "valor_transacao",
        "merchant_transacao",
        "resumo_descricao",
        "reason",
        "status",
        "suggested_category",
        "confianca_transacao",
        "created_at",
        "resolved_at",
    )
    list_filter = (
        "status",
        "reason",
        "created_at",
        "suggested_category__kind",
        "transaction__classification_source",
    )
    search_fields = (
        "id",
        "transaction__id",
        "transaction__description_raw",
        "transaction__description_norm",
        "transaction__merchant_norm",
        "transaction__raw_hash",
        "suggested_category__name",
        "resolution_note",
    )
    autocomplete_fields = ("transaction", "suggested_category")
    list_select_related = ("transaction", "suggested_category")
    readonly_fields = (
        "created_at",
        "resolucao_atual",
        "resumo_transacao",
    )
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    list_per_page = 100
    fields = (
        "transaction",
        "resumo_transacao",
        "status",
        "reason",
        "suggested_category",
        "categoria_final",
        "criar_merchant_map",
        "resolution_note",
        "resolucao_atual",
        "created_at",
    )

    @admin.action(description="Marcar pendências selecionadas como ignoradas")
    def marcar_como_ignorada(self, request, queryset):
        atualizadas = queryset.filter(status=ReviewQueue.Status.PENDING).update(
            status=ReviewQueue.Status.IGNORED,
            resolved_at=timezone.now(),
        )
        self.message_user(
            request,
            f"{atualizadas} pendência(s) marcada(s) como ignorada(s).",
            level=messages.INFO,
        )

    @admin.action(description="Criar MerchantMap para pendências selecionadas")
    def criar_merchant_map_para_selecionadas(self, request, queryset: QuerySet[ReviewQueue]) -> None:
        criadas = 0
        ignoradas = 0
        erros = 0
        for revisao in queryset.select_related("transaction", "transaction__category"):
            categoria = revisao.transaction.category
            if categoria is None:
                ignoradas += 1
                continue
            try:
                resultado = revisar_transacao_manualmente(
                    review_queue_id=revisao.id,
                    categoria_final_id=categoria.id,
                    criar_merchant_map=True,
                )
            except ValueError:
                erros += 1
                continue
            if resultado.merchant_map_criado:
                criadas += 1
            else:
                ignoradas += 1

        self.message_user(
            request,
            f"MerchantMaps criados: {criadas}. Ignoradas: {ignoradas}. Erros: {erros}.",
            level=messages.INFO,
        )

    @admin.display(description="Data transação", ordering="transaction__transaction_date")
    def data_transacao(self, obj: ReviewQueue):
        return obj.transaction.transaction_date

    @admin.display(description="Valor", ordering="transaction__amount")
    def valor_transacao(self, obj: ReviewQueue):
        return obj.transaction.amount

    @admin.display(description="Merchant", ordering="transaction__merchant_norm")
    def merchant_transacao(self, obj: ReviewQueue):
        return obj.transaction.merchant_norm or "—"

    @admin.display(description="Descrição", ordering="transaction__description_raw")
    def resumo_descricao(self, obj: ReviewQueue):
        descricao = obj.transaction.description_raw or ""
        return Truncator(descricao).chars(60)

    @admin.display(description="Confiança", ordering="transaction__classification_confidence")
    def confianca_transacao(self, obj: ReviewQueue):
        return obj.transaction.classification_confidence

    @admin.display(description="Resumo da transação")
    def resumo_transacao(self, obj: ReviewQueue):
        transacao = obj.transaction
        return format_html(
            "<b>Data:</b> {}<br><b>Valor:</b> {}<br><b>Merchant:</b> {}<br><b>Descrição:</b> {}<br><b>Origem:</b> {}",
            transacao.transaction_date,
            transacao.amount,
            transacao.merchant_norm or "—",
            Truncator(transacao.description_raw or "").chars(120),
            transacao.get_classification_source_display(),
        )

    @admin.display(description="Estado atual da resolução")
    def resolucao_atual(self, obj: ReviewQueue):
        if obj.status == ReviewQueue.Status.PENDING:
            return "Pendente"
        return f"{obj.get_status_display()} em {obj.resolved_at or 'sem data'}"

    def save_model(self, request, obj: ReviewQueue, form, change) -> None:
        categoria_final = form.cleaned_data.get("categoria_final")
        criar_merchant_map = form.cleaned_data.get("criar_merchant_map", False)
        if categoria_final:
            resultado = revisar_transacao_manualmente(
                review_queue_id=obj.id,
                categoria_final_id=categoria_final.id,
                criar_merchant_map=criar_merchant_map,
                nota_resolucao=obj.resolution_note,
            )
            if resultado.ja_resolvida:
                self.message_user(
                    request,
                    "A pendência já estava resolvida e foi mantida sem alterações.",
                    level=messages.WARNING,
                )
                return
            mensagem = "Revisão manual aplicada com sucesso."
            if criar_merchant_map:
                if resultado.merchant_map_criado:
                    mensagem += " MerchantMap criado."
                elif resultado.merchant_map_existente:
                    mensagem += " MerchantMap já existente."
                else:
                    mensagem += " MerchantMap não criado por merchant_norm inválido."
            self.message_user(request, mensagem, level=messages.SUCCESS)
            return

        super().save_model(request, obj, form, change)
