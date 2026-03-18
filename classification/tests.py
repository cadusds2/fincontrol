from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from accounts.models import Account
from classification.models import Category, ReviewQueue
from imports.models import ImportBatch
from reports.models import Budget
from transactions.models import Transaction


class ReviewQueueModelTests(TestCase):
    def setUp(self) -> None:
        self.account = Account.objects.create(
            bank_name="Nubank",
            account_type=Account.TipoConta.CONTA_CORRENTE,
            display_name="Conta Principal",
        )
        self.import_batch = ImportBatch.objects.create(
            account=self.account,
            file_type=ImportBatch.TipoArquivo.EXTRATO_CONTA_NUBANK,
            source_filename="extrato.csv",
            status=ImportBatch.Status.RECEBIDO,
            imported_at=timezone.now(),
        )

    def _create_transaction(self, raw_hash: str = "hash-1") -> Transaction:
        return Transaction.objects.create(
            import_batch=self.import_batch,
            account=self.account,
            transaction_date=date(2026, 1, 10),
            description_raw="Compra mercado",
            description_norm="compra mercado",
            merchant_norm="mercado",
            amount="120.00",
            currency="BRL",
            direction=Transaction.Direction.DEBITO,
            raw_hash=raw_hash,
        )

    def test_clean_rejects_resolved_without_resolved_at(self) -> None:
        review_item = ReviewQueue(
            transaction=self._create_transaction(),
            reason=ReviewQueue.Reason.BAIXA_CONFIANCA,
            status=ReviewQueue.Status.RESOLVIDA,
        )

        with self.assertRaises(ValidationError):
            review_item.clean()

    def test_save_rejects_resolved_without_resolved_at(self) -> None:
        with self.assertRaises(ValidationError):
            ReviewQueue.objects.create(
                transaction=self._create_transaction(raw_hash="hash-2"),
                reason=ReviewQueue.Reason.SEM_CORRESPONDENCIA,
                status=ReviewQueue.Status.IGNORADA,
            )

    def test_save_allows_pending_without_resolved_at(self) -> None:
        review_item = ReviewQueue.objects.create(
            transaction=self._create_transaction(raw_hash="hash-3"),
            reason=ReviewQueue.Reason.CONFLITO,
            status=ReviewQueue.Status.PENDENTE,
        )

        self.assertIsNone(review_item.resolved_at)


class CategoryModelTests(TestCase):
    def test_kind_change_to_tecnica_is_blocked_when_category_has_budget(self) -> None:
        category = Category.objects.create(
            name="Alimentação",
            slug="alimentacao",
            kind=Category.Kind.CONSUMO,
            is_reportable=True,
        )
        Budget.objects.create(
            period_month="2026-03",
            category=category,
            planned_amount="800.00",
        )

        category.kind = Category.Kind.TECNICA
        category.is_reportable = False
        with self.assertRaises(ValidationError) as ctx:
            category.save()

        self.assertIn("kind", ctx.exception.message_dict)

    def test_kind_change_to_tecnica_is_allowed_without_budget(self) -> None:
        category = Category.objects.create(
            name="Reserva técnica",
            slug="reserva-tecnica",
            kind=Category.Kind.CONSUMO,
            is_reportable=True,
        )

        category.kind = Category.Kind.TECNICA
        category.is_reportable = False
        category.save()

        self.assertEqual(category.kind, Category.Kind.TECNICA)
