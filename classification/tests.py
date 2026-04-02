"""Testes do pipeline de classificação MVP."""

from datetime import date
from decimal import Decimal

from django.test import TestCase

from accounts.models import Account
from classification.models import Category, MerchantMap, ReviewQueue
from classification.services.classification_service import classificar_transacao
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
