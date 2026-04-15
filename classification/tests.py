"""Testes do pipeline de classificação MVP."""

from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.test.utils import override_settings

from accounts.models import Account
from classification.models import Category, MerchantMap, ReviewQueue
from classification.services.classification_service import classificar_transacao
from classification.services.manual_review_service import revisar_transacao_manualmente
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

    def criar_transacao(self, descricao_norm: str, merchant_norm: str) -> Transaction:
        return Transaction.objects.create(
            import_batch=self.lote,
            account=self.conta,
            transaction_date=date(2026, 4, 1),
            description_raw=descricao_norm,
            description_norm=descricao_norm,
            merchant_raw=merchant_norm,
            merchant_norm=merchant_norm,
            amount=Decimal("10.00"),
            direction=Transaction.Direction.DEBIT,
            raw_hash=f"hash-{descricao_norm}-{merchant_norm}",
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

    def criar_transacao_com_revisao(self, merchant_norm: str = "loja xpto") -> tuple[Transaction, ReviewQueue]:
        transacao = Transaction.objects.create(
            import_batch=self.lote,
            account=self.conta,
            transaction_date=date(2026, 4, 2),
            description_raw="compra sem match",
            description_norm="compra sem match",
            merchant_raw=merchant_norm,
            merchant_norm=merchant_norm,
            amount=Decimal("50.00"),
            direction=Transaction.Direction.DEBIT,
            raw_hash=f"hash-revisao-{merchant_norm}",
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

        # Regressão: Transaction.category é nullable, então não deve entrar em
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
