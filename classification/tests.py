"""Testes do pipeline de classificação MVP."""

from datetime import date
from decimal import Decimal
import hashlib

import yaml
from django.contrib import admin as django_admin
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.test import RequestFactory
from django.test.utils import override_settings
from django.urls import reverse

from accounts.models import Account
from classification.admin import ClassificationRuleSetAdmin
from classification.models import Category, ClassificationRuleSet, MerchantMap, ReviewQueue
from classification.services.classification_service import classificar_transacao
from classification.services.manual_review_service import revisar_transacao_manualmente
from classification.services.yaml_rules import anexar_regra_yaml, ativar_ruleset, validar_yaml_ruleset
from imports.models import ImportBatch
from transactions.models import Transaction


class ClassificacaoMvpTests(TestCase):
    def setUp(self) -> None:
        self.conta = Account.objects.create(
            bank_name="Nubank",
            account_type=Account.AccountType.CHECKING,
            display_name="Conta principal",
        )
        self.lote = ImportBatch.objects.create(
            account=self.conta,
            file_type=ImportBatch.FileType.EXTRATO_CONTA_NUBANK,
            source_filename="arquivo.csv",
        )

        self.categoria_alimentacao = Category.objects.create(
            name="Alimentação",
            slug="alimentacao",
            kind=Category.Kind.CONSUMO,
            is_reportable=True,
        )
        self.categoria_pagamento_fatura = Category.objects.create(
            name="Pagamento de Fatura",
            slug="pagamento-de-fatura",
            kind=Category.Kind.TECNICA,
            is_reportable=False,
        )
        self.categoria_transferencia_interna = Category.objects.create(
            name="Transferência Interna",
            slug="transferencia-interna",
            kind=Category.Kind.TECNICA,
            is_reportable=False,
        )
        self.categoria_movimentacao_investimentos = Category.objects.create(
            name="Movimentação de Investimentos",
            slug="movimentacao-de-investimentos",
            kind=Category.Kind.TECNICA,
            is_reportable=False,
        )

    def criar_transacao(
        self,
        descricao_norm: str,
        merchant_norm: str,
        *,
        amount: Decimal = Decimal("10.00"),
        direction: str = Transaction.Direction.DEBIT,
        external_id: str | None = None,
    ) -> Transaction:
        return Transaction.objects.create(
            import_batch=self.lote,
            account=self.conta,
            transaction_date=date(2026, 4, 1),
            description_raw=descricao_norm,
            description_norm=descricao_norm,
            merchant_raw=merchant_norm,
            merchant_norm=merchant_norm,
            amount=amount,
            direction=direction,
            external_id=external_id,
            raw_hash=hashlib.sha256(
                f"{descricao_norm}|{merchant_norm}|{amount}|{direction}|{external_id}".encode("utf-8")
            ).hexdigest(),
        )

    def test_classifica_por_merchant_map(self) -> None:
        MerchantMap.objects.create(
            merchant_norm="padaria sao jose",
            category=self.categoria_alimentacao,
            source=MerchantMap.Source.SEED,
            confidence=Decimal("0.900"),
        )
        transacao = self.criar_transacao("compra no debito", "padaria sao jose")

        resultado = classificar_transacao(transacao)
        transacao.refresh_from_db()

        self.assertEqual(resultado.origem, Transaction.ClassificationSource.MERCHANT_MAP)
        self.assertEqual(transacao.category, self.categoria_alimentacao)
        self.assertEqual(transacao.classification_source, Transaction.ClassificationSource.MERCHANT_MAP)
        self.assertEqual(transacao.classification_confidence, Decimal("0.99"))
        self.assertFalse(ReviewQueue.objects.filter(transaction=transacao).exists())

    def test_classifica_por_regra_deterministica(self) -> None:
        transacao = self.criar_transacao(
            "pagamento de fatura cartao nubank",
            "pagamento de fatura cartao nubank",
        )

        resultado = classificar_transacao(transacao)
        transacao.refresh_from_db()

        self.assertEqual(resultado.origem, Transaction.ClassificationSource.RULE)
        self.assertEqual(transacao.category, self.categoria_pagamento_fatura)
        self.assertEqual(transacao.classification_source, Transaction.ClassificationSource.RULE)
        self.assertEqual(transacao.classification_confidence, Decimal("0.95"))
        self.assertFalse(ReviewQueue.objects.filter(transaction=transacao).exists())

    def test_ruleset_yaml_considera_merchant_norm_para_regra_tecnica(self) -> None:
        transacao = self.criar_transacao(
            "lancamento tecnico",
            "pagamento de fatura",
        )

        resultado = classificar_transacao(transacao)
        transacao.refresh_from_db()

        self.assertEqual(resultado.origem, Transaction.ClassificationSource.RULE)
        self.assertEqual(transacao.category, self.categoria_pagamento_fatura)
        self.assertEqual(transacao.classification_confidence, Decimal("0.95"))

    def test_classifica_transferencia_interna_por_ruleset_yaml(self) -> None:
        transacao = self.criar_transacao(
            "transferencia entre contas",
            "transferencia entre contas",
        )

        resultado = classificar_transacao(transacao)
        transacao.refresh_from_db()

        self.assertEqual(resultado.origem, Transaction.ClassificationSource.RULE)
        self.assertEqual(transacao.category, self.categoria_transferencia_interna)
        self.assertEqual(transacao.classification_confidence, Decimal("0.95"))

    def test_pagamento_de_fatura_prioriza_regra_tecnica_sobre_merchant_map(self) -> None:
        MerchantMap.objects.create(
            merchant_norm="pagamento de fatura",
            category=self.categoria_alimentacao,
            source=MerchantMap.Source.SEED,
            confidence=Decimal("0.900"),
        )
        transacao = self.criar_transacao("pagamento de fatura", "pagamento de fatura")

        classificar_transacao(transacao)
        transacao.refresh_from_db()

        self.assertEqual(transacao.category, self.categoria_pagamento_fatura)
        self.assertEqual(transacao.category.kind, Category.Kind.TECNICA)
        self.assertFalse(transacao.category.is_reportable)
        self.assertEqual(transacao.classification_source, Transaction.ClassificationSource.RULE)

    def test_aplicacao_rdb_classifica_como_movimentacao_de_investimentos(self) -> None:
        transacao = self.criar_transacao("aplicacao rdb", "aplicacao rdb")

        classificar_transacao(transacao)
        transacao.refresh_from_db()

        self.assertEqual(transacao.category, self.categoria_movimentacao_investimentos)
        self.assertEqual(transacao.category.kind, Category.Kind.TECNICA)
        self.assertFalse(transacao.category.is_reportable)
        self.assertEqual(transacao.classification_source, Transaction.ClassificationSource.RULE)

    def test_merchant_map_mantem_precedencia_sobre_regra_yaml_comum(self) -> None:
        categoria_outros = Category.objects.create(
            name="Outros",
            slug="outros",
            kind=Category.Kind.CONSUMO,
            is_reportable=True,
        )
        ruleset = ClassificationRuleSet.objects.create(
            name="Regra comum padaria",
            version=2,
            status=ClassificationRuleSet.Status.DRAFT,
            yaml_content="""version: 2
rules:
  - id: padaria_generica
    priority: 100
    category_slug: outros
    confidence: "0.80"
    when:
      all:
        - field: merchant_norm
          contains: padaria
""",
        )
        ativar_ruleset(ruleset)
        MerchantMap.objects.create(
            merchant_norm="padaria sao jose",
            category=self.categoria_alimentacao,
            source=MerchantMap.Source.SEED,
            confidence=Decimal("0.900"),
        )
        transacao = self.criar_transacao("compra no debito", "padaria sao jose")

        classificar_transacao(transacao)
        transacao.refresh_from_db()

        self.assertEqual(transacao.category, self.categoria_alimentacao)
        self.assertEqual(transacao.classification_source, Transaction.ClassificationSource.MERCHANT_MAP)
        self.assertNotEqual(transacao.category, categoria_outros)

    def test_par_pix_credito_mesmo_external_id_fica_fora_do_consumo(self) -> None:
        external_id = "pix-credito-001"
        credito = self.criar_transacao(
            "valor adicionado na conta por cartao de credito valor adicionado para pix no credito",
            "valor adicionado para pix no credito",
            amount=Decimal("160.00"),
            direction=Transaction.Direction.CREDIT,
            external_id=external_id,
        )
        debito = self.criar_transacao(
            "transferencia enviada pelo pix debora ferreira alves",
            "debora ferreira alves",
            amount=Decimal("160.00"),
            direction=Transaction.Direction.DEBIT,
            external_id=external_id,
        )
        ReviewQueue.objects.create(
            transaction=credito,
            reason=ReviewQueue.Reason.NO_MATCH,
            status=ReviewQueue.Status.PENDING,
        )

        classificar_transacao(debito)
        credito.refresh_from_db()
        debito.refresh_from_db()

        self.assertEqual(credito.category, self.categoria_transferencia_interna)
        self.assertEqual(debito.category, self.categoria_transferencia_interna)
        self.assertEqual(credito.classification_source, Transaction.ClassificationSource.RULE)
        self.assertEqual(debito.classification_source, Transaction.ClassificationSource.RULE)
        self.assertFalse(credito.category.is_reportable)
        self.assertEqual(ReviewQueue.objects.get(transaction=credito).status, ReviewQueue.Status.RESOLVED)

    @override_settings(
        CLASSIFICACAO_ALIASES_TITULAR={
            "padrao": ["joao da silva"],
            "por_conta": {},
        }
    )
    def test_classifica_transferencia_interna_por_alias_titular(self) -> None:
        transacao = self.criar_transacao(
            "pix enviado para joao da silva",
            "joao da silva",
        )

        resultado = classificar_transacao(transacao)
        transacao.refresh_from_db()

        self.assertEqual(resultado.origem, Transaction.ClassificationSource.RULE)
        self.assertEqual(transacao.category, self.categoria_transferencia_interna)
        self.assertEqual(transacao.classification_source, Transaction.ClassificationSource.RULE)
        self.assertEqual(transacao.classification_confidence, Decimal("0.98"))
        self.assertFalse(ReviewQueue.objects.filter(transaction=transacao).exists())

    @override_settings(
        CLASSIFICACAO_ALIASES_TITULAR={
            "padrao": [],
            "por_conta": {
                "conta-principal": ["maria titular"],
            },
        }
    )
    def test_alias_titular_por_conta_nao_afeta_terceiros(self) -> None:
        self.conta.external_ref = "conta-principal"
        self.conta.save(update_fields=["external_ref", "updated_at"])
        transacao = self.criar_transacao(
            "pix enviado para ana terceiros",
            "ana terceiros",
        )

        resultado = classificar_transacao(transacao)
        transacao.refresh_from_db()

        self.assertEqual(resultado.origem, Transaction.ClassificationSource.UNCLASSIFIED)
        self.assertIsNone(transacao.category)
        self.assertEqual(transacao.classification_source, Transaction.ClassificationSource.UNCLASSIFIED)
        self.assertEqual(ReviewQueue.objects.filter(transaction=transacao).count(), 1)

    def test_fallback_cria_review_queue_quando_sem_match(self) -> None:
        transacao = self.criar_transacao("compra completamente nova", "loja sem historico")

        resultado = classificar_transacao(transacao)
        transacao.refresh_from_db()

        self.assertEqual(resultado.origem, Transaction.ClassificationSource.UNCLASSIFIED)
        self.assertIsNone(transacao.category)
        self.assertEqual(transacao.classification_source, Transaction.ClassificationSource.UNCLASSIFIED)
        self.assertIsNone(transacao.classification_confidence)
        self.assertEqual(ReviewQueue.objects.filter(transaction=transacao).count(), 1)

    def test_reexecucao_nao_duplica_review_queue(self) -> None:
        transacao = self.criar_transacao("compra sem match", "sem-match")

        classificar_transacao(transacao)
        classificar_transacao(transacao)

        self.assertEqual(ReviewQueue.objects.filter(transaction=transacao).count(), 1)

    def test_classificacao_posterior_resolve_review_queue_pendente(self) -> None:
        transacao = self.criar_transacao("compra sem match", "sem-match")
        classificar_transacao(transacao)

        MerchantMap.objects.create(
            merchant_norm="sem-match",
            category=self.categoria_alimentacao,
            source=MerchantMap.Source.MANUAL_REVIEW,
        )

        classificar_transacao(transacao)
        transacao.refresh_from_db()
        review = ReviewQueue.objects.get(transaction=transacao)

        self.assertEqual(transacao.classification_source, Transaction.ClassificationSource.MERCHANT_MAP)
        self.assertEqual(review.status, ReviewQueue.Status.RESOLVED)

    def test_regressao_classificacao_com_categoria_nula_sem_excecao_de_for_update(self) -> None:
        MerchantMap.objects.create(
            merchant_norm="cafeteria azul",
            category=self.categoria_alimentacao,
            source=MerchantMap.Source.SEED,
            confidence=Decimal("0.920"),
        )
        transacao = self.criar_transacao("compra no debito", "cafeteria azul")
        self.assertIsNone(transacao.category_id)

        # Regressão: Transaction.category é nullable, então não deve entrar em
        # select_related quando a consulta usa select_for_update.
        resultado = classificar_transacao(transacao)
        transacao.refresh_from_db()

        self.assertEqual(resultado.origem, Transaction.ClassificationSource.MERCHANT_MAP)
        self.assertEqual(transacao.category, self.categoria_alimentacao)
        self.assertEqual(transacao.classification_source, Transaction.ClassificationSource.MERCHANT_MAP)


class RevisaoManualServiceTests(TestCase):
    def setUp(self) -> None:
        self.conta = Account.objects.create(
            bank_name="Nubank",
            account_type=Account.AccountType.CHECKING,
            display_name="Conta revisão manual",
        )
        self.lote = ImportBatch.objects.create(
            account=self.conta,
            file_type=ImportBatch.FileType.EXTRATO_CONTA_NUBANK,
            source_filename="revisao.csv",
        )
        self.categoria_outros = Category.objects.create(
            name="Outros",
            slug="outros",
            kind=Category.Kind.CONSUMO,
            is_reportable=True,
        )

    def criar_transacao_com_revisao(
        self,
        merchant_norm: str = "loja xpto",
        *,
        description_norm: str = "compra sem match",
    ) -> tuple[Transaction, ReviewQueue]:
        transacao = Transaction.objects.create(
            import_batch=self.lote,
            account=self.conta,
            transaction_date=date(2026, 4, 2),
            description_raw=description_norm,
            description_norm=description_norm,
            merchant_raw=merchant_norm,
            merchant_norm=merchant_norm,
            amount=Decimal("50.00"),
            direction=Transaction.Direction.DEBIT,
            raw_hash=hashlib.sha256(
                f"revisao|{merchant_norm}|{description_norm}".encode("utf-8")
            ).hexdigest(),
            classification_source=Transaction.ClassificationSource.UNCLASSIFIED,
        )
        revisao = ReviewQueue.objects.create(
            transaction=transacao,
            reason=ReviewQueue.Reason.NO_MATCH,
            status=ReviewQueue.Status.PENDING,
        )
        return transacao, revisao

    def test_revisao_manual_atualiza_transaction_e_resolve_review_queue(self) -> None:
        transacao, revisao = self.criar_transacao_com_revisao()

        revisar_transacao_manualmente(
            review_queue_id=revisao.id,
            categoria_final_id=self.categoria_outros.id,
        )

        transacao.refresh_from_db()
        revisao.refresh_from_db()
        self.assertEqual(transacao.category, self.categoria_outros)
        self.assertEqual(transacao.classification_source, Transaction.ClassificationSource.MANUAL)
        self.assertEqual(transacao.classification_confidence, Decimal("1.00"))
        self.assertEqual(revisao.status, ReviewQueue.Status.RESOLVED)
        self.assertIsNotNone(revisao.resolved_at)

    def test_revisao_manual_pode_criar_merchant_map(self) -> None:
        _, revisao = self.criar_transacao_com_revisao(merchant_norm="super mercado bom")

        resultado = revisar_transacao_manualmente(
            review_queue_id=revisao.id,
            categoria_final_id=self.categoria_outros.id,
            criar_merchant_map=True,
        )

        self.assertTrue(resultado.merchant_map_criado)
        self.assertTrue(
            MerchantMap.objects.filter(
                merchant_norm="super mercado bom",
                category=self.categoria_outros,
            ).exists()
        )

    def test_revisao_manual_nao_duplica_merchant_map_existente(self) -> None:
        _, revisao = self.criar_transacao_com_revisao(merchant_norm="padaria central")
        MerchantMap.objects.create(
            merchant_norm="padaria central",
            category=self.categoria_outros,
            source=MerchantMap.Source.SEED,
        )

        resultado = revisar_transacao_manualmente(
            review_queue_id=revisao.id,
            categoria_final_id=self.categoria_outros.id,
            criar_merchant_map=True,
        )

        self.assertFalse(resultado.merchant_map_criado)
        self.assertTrue(resultado.merchant_map_existente)
        self.assertEqual(
            MerchantMap.objects.filter(
                merchant_norm="padaria central",
                category=self.categoria_outros,
            ).count(),
            1,
        )

    def test_revisao_manual_nao_cria_merchant_map_sem_merchant_norm_util(self) -> None:
        _, revisao = self.criar_transacao_com_revisao(merchant_norm="   ")

        resultado = revisar_transacao_manualmente(
            review_queue_id=revisao.id,
            categoria_final_id=self.categoria_outros.id,
            criar_merchant_map=True,
        )

        self.assertFalse(resultado.merchant_map_criado)
        self.assertFalse(resultado.merchant_map_existente)
        self.assertEqual(MerchantMap.objects.count(), 0)

    def test_revisao_manual_nao_cria_merchant_map_para_transferencia_pix(self) -> None:
        _, revisao = self.criar_transacao_com_revisao(
            merchant_norm="carlos eduardo santos da silva",
            description_norm="transferencia recebida pelo pix carlos eduardo santos da silva",
        )

        resultado = revisar_transacao_manualmente(
            review_queue_id=revisao.id,
            categoria_final_id=self.categoria_outros.id,
            criar_merchant_map=True,
        )

        self.assertFalse(resultado.merchant_map_criado)
        self.assertFalse(resultado.merchant_map_existente)
        self.assertEqual(MerchantMap.objects.count(), 0)

    def test_revisao_manual_idempotente_para_review_ja_resolvida(self) -> None:
        transacao, revisao = self.criar_transacao_com_revisao()
        revisar_transacao_manualmente(
            review_queue_id=revisao.id,
            categoria_final_id=self.categoria_outros.id,
        )

        resultado = revisar_transacao_manualmente(
            review_queue_id=revisao.id,
            categoria_final_id=self.categoria_outros.id,
        )
        transacao.refresh_from_db()
        revisao.refresh_from_db()

        self.assertTrue(resultado.ja_resolvida)
        self.assertEqual(transacao.classification_source, Transaction.ClassificationSource.MANUAL)
        self.assertEqual(revisao.status, ReviewQueue.Status.RESOLVED)

    def test_regressao_revisao_manual_com_categoria_nula_sem_excecao_de_for_update(self) -> None:
        transacao, revisao = self.criar_transacao_com_revisao(merchant_norm="banca central")
        self.assertIsNone(transacao.category_id)

        # Regressao: Transaction.category e nullable, entao nao deve entrar em
        # select_related quando a consulta usa select_for_update.
        resultado = revisar_transacao_manualmente(
            review_queue_id=revisao.id,
            categoria_final_id=self.categoria_outros.id,
        )
        transacao.refresh_from_db()
        revisao.refresh_from_db()

        self.assertFalse(resultado.ja_resolvida)
        self.assertEqual(transacao.category_id, self.categoria_outros.id)
        self.assertEqual(transacao.classification_source, Transaction.ClassificationSource.MANUAL)
        self.assertEqual(revisao.status, ReviewQueue.Status.RESOLVED)


class ClassificationRuleSetYamlTests(TestCase):
    def setUp(self) -> None:
        self.categoria_outros = Category.objects.create(
            name="Outros",
            slug="outros",
            kind=Category.Kind.CONSUMO,
            is_reportable=True,
        )

    def test_valida_yaml_valido(self) -> None:
        resultado = validar_yaml_ruleset("""version: 1
rules:
  - id: credito_em_conta
    priority: 10
    category_slug: outros
    confidence: "0.80"
    when:
      all:
        - field: direction
          equals: credit
""")

        self.assertTrue(resultado.valid)
        self.assertEqual(resultado.errors, ())
        self.assertTrue(resultado.checksum)

    def test_bloqueia_yaml_malformado(self) -> None:
        resultado = validar_yaml_ruleset("version: [")

        self.assertFalse(resultado.valid)
        self.assertIn("YAML invalido", resultado.errors[0])

    def test_bloqueia_campos_obrigatorios_ausentes(self) -> None:
        resultado = validar_yaml_ruleset("""version: 1
rules:
  - id: incompleta
    category_slug: outros
    when:
      all:
        - field: direction
          equals: credit
""")

        self.assertFalse(resultado.valid)
        self.assertTrue(any("'priority' deve ser inteiro" in erro for erro in resultado.errors))
        self.assertTrue(any("'confidence' deve ser decimal" in erro for erro in resultado.errors))

    def test_bloqueia_categoria_inexistente_ou_inativa(self) -> None:
        resultado = validar_yaml_ruleset("""version: 1
rules:
  - id: categoria_invalida
    priority: 10
    category_slug: inexistente
    confidence: "0.80"
    when:
      all:
        - field: direction
          equals: credit
""")

        self.assertFalse(resultado.valid)
        self.assertTrue(any("categoria ativa 'inexistente' nao encontrada" in erro for erro in resultado.errors))

    def test_bloqueia_field_e_operador_fora_da_whitelist(self) -> None:
        resultado = validar_yaml_ruleset("""version: 1
rules:
  - id: operador_invalido
    priority: 10
    category_slug: outros
    confidence: "0.80"
    when:
      all:
        - field: amount
          regex: ".*"
""")

        self.assertFalse(resultado.valid)
        self.assertTrue(any("field 'amount' invalido" in erro for erro in resultado.errors))
        self.assertTrue(any("operador 'regex' invalido" in erro for erro in resultado.errors))

    def test_ativacao_mantem_apenas_um_ruleset_ativo(self) -> None:
        ruleset = ClassificationRuleSet.objects.create(
            name="Novo ruleset",
            version=2,
            status=ClassificationRuleSet.Status.DRAFT,
            yaml_content="""version: 2
rules:
  - id: credito_em_conta
    priority: 10
    category_slug: outros
    confidence: "0.80"
    when:
      all:
        - field: direction
          equals: credit
""",
        )

        resultado = ativar_ruleset(ruleset)

        self.assertTrue(resultado.valid)
        self.assertEqual(
            ClassificationRuleSet.objects.filter(status=ClassificationRuleSet.Status.ACTIVE).count(),
            1,
        )
        ruleset.refresh_from_db()
        self.assertEqual(ruleset.status, ClassificationRuleSet.Status.ACTIVE)
        self.assertTrue(ruleset.checksum)

    def test_anexa_regra_yaml_em_conteudo_vazio(self) -> None:
        novo_yaml, resultado = anexar_regra_yaml(
            "",
            {
                "id": "spotify_assinatura",
                "priority": 80,
                "category_slug": "outros",
                "confidence": "0.90",
                "when": {
                    "all": [
                        {"field": "merchant_norm", "contains": "spotify"},
                    ]
                },
            },
            default_version=2,
        )

        self.assertTrue(resultado.valid)
        parsed = yaml.safe_load(novo_yaml)
        self.assertEqual(parsed["version"], 2)
        self.assertEqual(parsed["rules"][0]["id"], "spotify_assinatura")

    def test_anexa_regra_yaml_bloqueia_id_duplicado(self) -> None:
        novo_yaml, resultado = anexar_regra_yaml(
            """version: 1
rules:
  - id: existente
    priority: 10
    category_slug: outros
    confidence: "0.80"
    when:
      all:
        - field: direction
          equals: credit
""",
            {
                "id": "existente",
                "priority": 20,
                "category_slug": "outros",
                "confidence": "0.90",
                "when": {
                    "all": [
                        {"field": "merchant_norm", "contains": "spotify"},
                    ]
                },
            },
            default_version=1,
        )

        self.assertIsNone(novo_yaml)
        self.assertFalse(resultado.valid)
        self.assertTrue(any("Ja existe uma regra com id 'existente'" in erro for erro in resultado.errors))


class ClassificationRuleSetAdminTests(TestCase):
    def setUp(self) -> None:
        self.categoria_outros = Category.objects.create(
            name="Outros",
            slug="outros",
            kind=Category.Kind.CONSUMO,
            is_reportable=True,
        )
        self.ruleset_rascunho = ClassificationRuleSet.objects.create(
            name="Rascunho guiado",
            version=2,
            status=ClassificationRuleSet.Status.DRAFT,
            yaml_content="",
        )
        User = get_user_model()
        self.user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="senha-admin",
        )

    def test_admin_exibe_instrucoes_yaml(self) -> None:
        ruleset = ClassificationRuleSet.objects.filter(status=ClassificationRuleSet.Status.ACTIVE).first()
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("admin:classification_classificationruleset_change", args=[ruleset.id])
        )

        self.assertContains(response, "Como editar regras YAML")
        self.assertContains(response, "Campos permitidos")
        self.assertContains(response, "contains_all")
        self.assertContains(response, "Resumo do YAML")
        self.assertContains(response, "Conteudo YAML")

    def test_ruleset_ativo_fica_somente_leitura_no_admin(self) -> None:
        ruleset = ClassificationRuleSet.objects.filter(status=ClassificationRuleSet.Status.ACTIVE).first()
        request = RequestFactory().get("/")
        request.user = self.user
        admin_model = ClassificationRuleSetAdmin(ClassificationRuleSet, django_admin.site)

        readonly_fields = admin_model.get_readonly_fields(request, ruleset)

        self.assertIn("yaml_content", readonly_fields)
        self.assertIn("status", readonly_fields)

    def test_admin_exibe_botao_adicionar_regra_para_rascunho(self) -> None:
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("admin:classification_classificationruleset_change", args=[self.ruleset_rascunho.id])
        )

        self.assertContains(response, "Adicionar regra via formulario")
        self.assertContains(response, "Conteudo YAML das regras")
        self.assertContains(response, "spellcheck")
        self.assertContains(response, "spotify_assinatura")
        self.assertContains(response, "admin/classification/yaml_editor.js")
        self.assertContains(response, "admin/classification/yaml_editor.css")

    def test_admin_add_orienta_salvar_antes_de_adicionar_regra(self) -> None:
        self.client.force_login(self.user)

        response = self.client.get(reverse("admin:classification_classificationruleset_add"))

        self.assertContains(response, "Salve o ruleset como rascunho antes de adicionar regras por formulario.")

    def test_admin_rota_add_adicionar_regra_nao_dispara_ruleset_nao_encontrado(self) -> None:
        self.client.force_login(self.user)

        response = self.client.get(
            "/admin/classification/classificationruleset/add/adicionar-regra/",
            follow=True,
        )

        self.assertNotContains(response, "Ruleset nao encontrado")

    def test_admin_bloqueia_gerador_para_ruleset_ativo(self) -> None:
        ruleset = ClassificationRuleSet.objects.filter(status=ClassificationRuleSet.Status.ACTIVE).first()
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("admin:classification_classificationruleset_add_rule", args=[ruleset.id])
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response["Location"],
            reverse("admin:classification_classificationruleset_change", args=[ruleset.id]),
        )

    def test_admin_gerador_cria_regra_simples_contains(self) -> None:
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("admin:classification_classificationruleset_add_rule", args=[self.ruleset_rascunho.id]),
            {
                "rule_id": "spotify_assinatura",
                "priority": "80",
                "category": str(self.categoria_outros.id),
                "confidence": "0.90",
                "combinator": "all",
                "condition_1_field": "merchant_norm",
                "condition_1_operator": "contains",
                "condition_1_value": "spotify",
                "condition_2_field": "",
                "condition_2_operator": "",
                "condition_2_value": "",
                "condition_3_field": "",
                "condition_3_operator": "",
                "condition_3_value": "",
            },
        )
        self.ruleset_rascunho.refresh_from_db()
        parsed = yaml.safe_load(self.ruleset_rascunho.yaml_content)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(parsed["rules"][0]["id"], "spotify_assinatura")
        self.assertEqual(parsed["rules"][0]["when"]["all"][0]["contains"], "spotify")
        self.assertTrue(self.ruleset_rascunho.checksum)
        self.assertEqual(self.ruleset_rascunho.validation_errors, "")
        self.assertTrue(validar_yaml_ruleset(self.ruleset_rascunho.yaml_content).valid)

    def test_admin_gerador_cria_regra_com_contains_all(self) -> None:
        self.client.force_login(self.user)

        self.client.post(
            reverse("admin:classification_classificationruleset_add_rule", args=[self.ruleset_rascunho.id]),
            {
                "rule_id": "aplicacao_rdb_teste",
                "priority": "90",
                "category": str(self.categoria_outros.id),
                "confidence": "0.95",
                "combinator": "any",
                "condition_1_field": "description_norm",
                "condition_1_operator": "contains_all",
                "condition_1_value": "aplicacao\r\nrdb",
                "condition_2_field": "",
                "condition_2_operator": "",
                "condition_2_value": "",
                "condition_3_field": "",
                "condition_3_operator": "",
                "condition_3_value": "",
            },
        )
        self.ruleset_rascunho.refresh_from_db()
        parsed = yaml.safe_load(self.ruleset_rascunho.yaml_content)

        self.assertEqual(
            parsed["rules"][0]["when"]["any"][0]["contains_all"],
            ["aplicacao", "rdb"],
        )

    def test_admin_gerador_bloqueia_id_duplicado(self) -> None:
        self.ruleset_rascunho.yaml_content = """version: 2
rules:
  - id: spotify_assinatura
    priority: 80
    category_slug: outros
    confidence: "0.90"
    when:
      all:
        - field: merchant_norm
          contains: spotify
"""
        self.ruleset_rascunho.save(update_fields=["yaml_content", "updated_at"])
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("admin:classification_classificationruleset_add_rule", args=[self.ruleset_rascunho.id]),
            {
                "rule_id": "spotify_assinatura",
                "priority": "85",
                "category": str(self.categoria_outros.id),
                "confidence": "0.90",
                "combinator": "all",
                "condition_1_field": "merchant_norm",
                "condition_1_operator": "contains",
                "condition_1_value": "spotify",
                "condition_2_field": "",
                "condition_2_operator": "",
                "condition_2_value": "",
                "condition_3_field": "",
                "condition_3_operator": "",
                "condition_3_value": "",
            },
        )
        self.ruleset_rascunho.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ja existe uma regra com id")
        self.assertIn("Ja existe uma regra com id", self.ruleset_rascunho.validation_errors)

    def test_admin_gerador_bloqueia_operador_incompativel_com_valor_vazio(self) -> None:
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("admin:classification_classificationruleset_add_rule", args=[self.ruleset_rascunho.id]),
            {
                "rule_id": "regra_vazia",
                "priority": "80",
                "category": str(self.categoria_outros.id),
                "confidence": "0.90",
                "combinator": "all",
                "condition_1_field": "merchant_norm",
                "condition_1_operator": "contains",
                "condition_1_value": "",
                "condition_2_field": "",
                "condition_2_operator": "",
                "condition_2_value": "",
                "condition_3_field": "",
                "condition_3_operator": "",
                "condition_3_value": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Preencha campo, operador e valor da condicao 1")

