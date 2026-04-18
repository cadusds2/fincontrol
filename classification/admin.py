"""Admin do app classification."""

from django import forms
from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.text import Truncator

from .models import Category, ClassificationRuleSet, MerchantMap, ReviewQueue
from .services.manual_review_service import revisar_transacao_manualmente
from .services.yaml_rules import (
    ALLOWED_FIELDS,
    ALLOWED_OPERATORS,
    RULE_ID_PATTERN,
    anexar_regra_yaml,
    ativar_ruleset,
    validar_yaml_ruleset,
)


class CategoryChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj: Category) -> str:
        return f"{obj.name} ({obj.slug})"


class RuleBuilderForm(forms.Form):
    COMBINATOR_CHOICES = (
        ("all", "Todas as condicoes (all)"),
        ("any", "Qualquer condicao (any)"),
    )

    rule_id = forms.RegexField(
        regex=RULE_ID_PATTERN,
        label="ID da regra",
        help_text="Use snake_case, por exemplo: spotify_assinatura.",
    )
    priority = forms.IntegerField(label="Prioridade", min_value=0, initial=80)
    category = CategoryChoiceField(
        queryset=Category.objects.filter(is_active=True).order_by("name"),
        label="Categoria",
    )
    confidence = forms.DecimalField(
        label="Confianca",
        min_value=0,
        max_value=1,
        decimal_places=2,
        initial="0.90",
    )
    combinator = forms.ChoiceField(label="Combinador", choices=COMBINATOR_CHOICES, initial="all")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field_choices = [("", "---------"), *[(field, field) for field in sorted(ALLOWED_FIELDS)]]
        operator_choices = [("", "---------"), *[(operator, operator) for operator in sorted(ALLOWED_OPERATORS)]]
        for index in range(1, 4):
            required = index == 1
            self.fields[f"condition_{index}_field"] = forms.ChoiceField(
                label=f"Condicao {index}: campo",
                choices=field_choices,
                required=required,
            )
            self.fields[f"condition_{index}_operator"] = forms.ChoiceField(
                label=f"Condicao {index}: operador",
                choices=operator_choices,
                required=required,
            )
            self.fields[f"condition_{index}_value"] = forms.CharField(
                label=f"Condicao {index}: valor",
                required=required,
                widget=forms.Textarea(attrs={"rows": 3}),
                help_text="Para contains_all e in, informe um valor por linha.",
            )

    def clean(self):
        cleaned_data = super().clean()
        conditions = []
        for index in range(1, 4):
            field = cleaned_data.get(f"condition_{index}_field")
            operator = cleaned_data.get(f"condition_{index}_operator")
            value = (cleaned_data.get(f"condition_{index}_value") or "").strip()
            filled = bool(field or operator or value)
            if index == 1 or filled:
                if not field or not operator or not value:
                    raise forms.ValidationError(f"Preencha campo, operador e valor da condicao {index}.")
                if operator in {"contains_all", "in"}:
                    values = [line.strip() for line in value.splitlines() if line.strip()]
                    if not values:
                        raise forms.ValidationError(f"A condicao {index} precisa de ao menos um valor.")
                    conditions.append({"field": field, operator: values})
                else:
                    conditions.append({"field": field, operator: value})

        if not conditions:
            raise forms.ValidationError("Informe ao menos uma condicao.")
        cleaned_data["conditions"] = conditions
        return cleaned_data

    def build_rule(self) -> dict:
        return {
            "id": self.cleaned_data["rule_id"],
            "priority": self.cleaned_data["priority"],
            "category_slug": self.cleaned_data["category"].slug,
            "confidence": f"{self.cleaned_data['confidence']:.2f}",
            "when": {
                self.cleaned_data["combinator"]: self.cleaned_data["conditions"],
            },
        }


class ClassificationRuleSetForm(forms.ModelForm):
    yaml_content = forms.CharField(
        label="Conteudo YAML das regras",
        required=False,
        help_text=(
            "Fonte final das regras. Voce pode editar manualmente ou usar "
            "'Adicionar regra via formulario' para inserir um bloco valido."
        ),
        widget=forms.Textarea(
            attrs={
                "rows": 34,
                "cols": 120,
                "spellcheck": "false",
                "wrap": "off",
                "placeholder": (
                    "version: 1\n"
                    "rules:\n"
                    "  - id: spotify_assinatura\n"
                    "    priority: 80\n"
                    "    category_slug: assinaturas\n"
                    "    confidence: \"0.90\"\n"
                    "    when:\n"
                    "      all:\n"
                    "        - field: merchant_norm\n"
                    "          contains: spotify\n"
                ),
                "style": (
                    "font-family: Consolas, 'Courier New', monospace; "
                    "font-size: 13px; line-height: 1.45; "
                    "max-width: 1180px; width: 100%; min-height: 560px; "
                    "tab-size: 2;"
                ),
            }
        ),
    )

    class Meta:
        model = ClassificationRuleSet
        fields = "__all__"

    class Media:
        css = {
            "all": ("admin/classification/yaml_editor.css",)
        }
        js = ("admin/classification/yaml_editor.js",)


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


@admin.register(ClassificationRuleSet)
class ClassificationRuleSetAdmin(admin.ModelAdmin):
    form = ClassificationRuleSetForm
    actions = ("validar_yaml", "ativar_rulesets", "duplicar_como_rascunho")
    list_display = (
        "name",
        "version",
        "status",
        "checksum_resumido",
        "activated_at",
        "updated_at",
    )
    list_filter = ("status", "activated_at", "updated_at")
    search_fields = ("name", "yaml_content", "validation_errors", "checksum")
    readonly_fields = (
        "instrucoes_yaml",
        "adicionar_regra_formulario",
        "resumo_yaml",
        "checksum",
        "validation_errors",
        "activated_at",
        "created_at",
        "updated_at",
    )
    fields = (
        "name",
        "version",
        "status",
        "instrucoes_yaml",
        "adicionar_regra_formulario",
        "resumo_yaml",
        "yaml_content",
        "validation_errors",
        "checksum",
        "activated_at",
        "created_at",
        "updated_at",
    )
    ordering = ("-version", "-updated_at")
    list_per_page = 50

    @admin.display(description="Checksum")
    def checksum_resumido(self, obj: ClassificationRuleSet):
        return obj.checksum[:12] if obj.checksum else "—"

    @admin.display(description="Adicionar regra")
    def adicionar_regra_formulario(self, obj: ClassificationRuleSet | None = None):
        if obj is None or obj.pk is None:
            return "Salve o ruleset como rascunho antes de adicionar regras por formulario."
        if obj.status != ClassificationRuleSet.Status.DRAFT:
            return "Disponivel apenas para rulesets em rascunho."
        url = reverse("admin:classification_classificationruleset_add_rule", args=[obj.pk])
        return format_html('<a class="button" href="{}">Adicionar regra via formulario</a>', url)

    @admin.display(description="Resumo do YAML")
    def resumo_yaml(self, obj: ClassificationRuleSet | None = None):
        if obj is None or not obj.yaml_content.strip():
            return "YAML vazio. Use o formulario guiado ou cole um YAML com version/rules."
        resultado = validar_yaml_ruleset(obj.yaml_content)
        if not resultado.valid or resultado.parsed is None:
            return format_html(
                '<span style="color:#ba2121;">YAML com {} erro(s) de validacao.</span>',
                len(resultado.errors),
            )
        rules = resultado.parsed.get("rules", [])
        version = resultado.parsed.get("version")
        rule_ids = [rule.get("id") for rule in rules if isinstance(rule, dict)]
        primeiras_regras = ", ".join(rule_ids[:5])
        sufixo = "..." if len(rule_ids) > 5 else ""
        return format_html(
            "Versao YAML: <strong>{}</strong> | Regras: <strong>{}</strong>{}",
            version,
            len(rules),
            format_html("<br>IDs: {}{}", primeiras_regras, sufixo) if primeiras_regras else "",
        )

    @admin.display(description="Como editar regras YAML")
    def instrucoes_yaml(self, obj: ClassificationRuleSet | None = None):
        return format_html(
            """
            <div style="max-width: 980px;">
              <p><strong>Estrutura minima:</strong> <code>version</code> e lista <code>rules</code>.</p>
              <p><strong>Campos permitidos:</strong> <code>description_norm</code>,
              <code>merchant_norm</code>, <code>direction</code>, <code>currency</code>.</p>
              <p><strong>Operadores:</strong> <code>contains</code>, <code>contains_all</code>,
              <code>equals</code>, <code>in</code>. Use <code>all</code> para exigir tudo e
              <code>any</code> para alternativas. Sem regex nesta versao.</p>
              <p><strong>Prioridade:</strong> numero maior roda antes. A primeira regra valida vence.
              Use <code>category_slug</code> de uma categoria ativa.</p>
              <p><strong>Operacao segura:</strong> crie ou duplique um rascunho, valide e so entao ative.
              Rulesets ativos ficam somente leitura.</p>
              <p><strong>Formulario guiado:</strong> em rulesets de rascunho, use o botao
              <em>Adicionar regra via formulario</em> para montar uma regra sem escrever YAML manualmente.</p>
              <pre style="background:#f6f8fa;border:1px solid #d0d7de;padding:12px;white-space:pre-wrap;">version: 1
rules:
  - id: pagamento_fatura
    priority: 100
    category_slug: pagamento-de-fatura
    confidence: "0.95"
    when:
      all:
        - field: description_norm
          contains_all:
            - pagamento
            - fatura

  - id: credito_em_conta
    priority: 70
    category_slug: outros
    confidence: "0.80"
    when:
      all:
        - field: direction
          equals: credit
        - field: description_norm
          contains: credito em conta

  - id: investimentos_basico
    priority: 95
    category_slug: movimentacao-de-investimentos
    confidence: "0.95"
    when:
      any:
        - field: description_norm
          contains_all:
            - aplicacao
            - rdb
        - field: description_norm
          contains_all:
            - resgate
            - investimento</pre>
            </div>
            """
        )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:object_id>/adicionar-regra/",
                self.admin_site.admin_view(self.adicionar_regra_view),
                name="classification_classificationruleset_add_rule",
            ),
        ]
        return custom_urls + urls

    def adicionar_regra_view(self, request, object_id):
        ruleset = self.get_object(request, object_id)
        if ruleset is None:
            self.message_user(request, "Ruleset nao encontrado.", level=messages.ERROR)
            return HttpResponseRedirect(reverse("admin:classification_classificationruleset_changelist"))

        change_url = reverse("admin:classification_classificationruleset_change", args=[ruleset.pk])
        if ruleset.status != ClassificationRuleSet.Status.DRAFT:
            self.message_user(
                request,
                "Regras so podem ser adicionadas por formulario em rulesets de rascunho.",
                level=messages.ERROR,
            )
            return HttpResponseRedirect(change_url)

        if request.method == "POST":
            form = RuleBuilderForm(request.POST)
            if form.is_valid():
                novo_yaml, resultado = anexar_regra_yaml(
                    ruleset.yaml_content,
                    form.build_rule(),
                    default_version=ruleset.version,
                )
                ruleset.checksum = resultado.checksum
                ruleset.validation_errors = "\n".join(resultado.errors)
                if novo_yaml is not None and resultado.valid:
                    ruleset.yaml_content = novo_yaml
                    ruleset.validation_errors = ""
                    ruleset.save(update_fields=["yaml_content", "checksum", "validation_errors", "updated_at"])
                    self.message_user(request, "Regra adicionada ao YAML do rascunho.", level=messages.SUCCESS)
                    return HttpResponseRedirect(change_url)
                ruleset.save(update_fields=["checksum", "validation_errors", "updated_at"])
                form.add_error(None, "\n".join(resultado.errors) or "Nao foi possivel adicionar a regra.")
        else:
            form = RuleBuilderForm()

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "original": ruleset,
            "title": "Adicionar regra via formulario",
            "form": form,
            "change_url": change_url,
            "media": self.media + form.media,
        }
        return TemplateResponse(
            request,
            "admin/classification/classificationruleset/rule_builder.html",
            context,
        )

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj and obj.status == ClassificationRuleSet.Status.ACTIVE:
            readonly.extend(["name", "version", "status", "yaml_content"])
        return tuple(readonly)

    def save_model(self, request, obj: ClassificationRuleSet, form, change) -> None:
        resultado = validar_yaml_ruleset(obj.yaml_content)
        ativar_apos_salvar = obj.status == ClassificationRuleSet.Status.ACTIVE and resultado.valid
        obj.checksum = resultado.checksum
        obj.validation_errors = "\n".join(resultado.errors)
        if obj.status == ClassificationRuleSet.Status.ACTIVE and not resultado.valid:
            self.message_user(
                request,
                "Ruleset ativo precisa ter YAML valido. Salve como rascunho e corrija os erros.",
                level=messages.ERROR,
            )
            obj.status = ClassificationRuleSet.Status.DRAFT
        if ativar_apos_salvar:
            obj.status = ClassificationRuleSet.Status.DRAFT
        super().save_model(request, obj, form, change)
        if ativar_apos_salvar:
            ativar_ruleset(obj)
            self.message_user(request, "YAML valido e ruleset ativado.", level=messages.SUCCESS)
        elif resultado.valid:
            self.message_user(request, "YAML valido.", level=messages.SUCCESS)
        else:
            self.message_user(request, "YAML salvo com erros de validacao.", level=messages.WARNING)

    @admin.action(description="Validar YAML")
    def validar_yaml(self, request, queryset: QuerySet[ClassificationRuleSet]) -> None:
        validos = 0
        invalidos = 0
        for ruleset in queryset:
            resultado = validar_yaml_ruleset(ruleset.yaml_content)
            ruleset.checksum = resultado.checksum
            ruleset.validation_errors = "\n".join(resultado.errors)
            ruleset.save(update_fields=["checksum", "validation_errors", "updated_at"])
            if resultado.valid:
                validos += 1
            else:
                invalidos += 1
        self.message_user(
            request,
            f"Rulesets validos: {validos}. Com erros: {invalidos}.",
            level=messages.INFO,
        )

    @admin.action(description="Ativar ruleset")
    def ativar_rulesets(self, request, queryset: QuerySet[ClassificationRuleSet]) -> None:
        if queryset.count() != 1:
            self.message_user(request, "Selecione exatamente um ruleset para ativar.", level=messages.ERROR)
            return
        ruleset = queryset.first()
        resultado = ativar_ruleset(ruleset)
        if resultado.valid:
            self.message_user(request, f"Ruleset '{ruleset}' ativado com sucesso.", level=messages.SUCCESS)
        else:
            self.message_user(
                request,
                "Ruleset nao ativado. Corrija os erros de validacao.",
                level=messages.ERROR,
            )

    @admin.action(description="Duplicar como rascunho")
    def duplicar_como_rascunho(self, request, queryset: QuerySet[ClassificationRuleSet]) -> None:
        criados = 0
        for ruleset in queryset:
            ClassificationRuleSet.objects.create(
                name=f"{ruleset.name} (copia)",
                version=ruleset.version + 1,
                status=ClassificationRuleSet.Status.DRAFT,
                yaml_content=ruleset.yaml_content,
                checksum=ruleset.checksum,
            )
            criados += 1
        self.message_user(request, f"Rascunhos criados: {criados}.", level=messages.SUCCESS)


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
