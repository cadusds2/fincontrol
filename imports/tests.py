from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from accounts.models import Account
from imports.models import ImportBatch
from transactions.models import Transaction


class ImportBatchModelTests(TestCase):
    def setUp(self) -> None:
        self.account_a = Account.objects.create(
            bank_name="Nubank",
            account_type=Account.TipoConta.CONTA_CORRENTE,
            display_name="Conta A",
        )
        self.account_b = Account.objects.create(
            bank_name="Itaú",
            account_type=Account.TipoConta.CONTA_CORRENTE,
            display_name="Conta B",
        )

    def test_account_reassignment_is_allowed_without_transactions(self) -> None:
        batch = ImportBatch.objects.create(
            account=self.account_a,
            file_type=ImportBatch.TipoArquivo.EXTRATO_CONTA_NUBANK,
            source_filename="extrato-sem-transacoes.csv",
            status=ImportBatch.Status.RECEBIDO,
            imported_at=timezone.now(),
        )

        batch.account = self.account_b
        batch.save()

        self.assertEqual(batch.account_id, self.account_b.id)

    def test_account_reassignment_is_blocked_when_batch_has_transactions(self) -> None:
        batch = ImportBatch.objects.create(
            account=self.account_a,
            file_type=ImportBatch.TipoArquivo.EXTRATO_CONTA_NUBANK,
            source_filename="extrato-com-transacoes.csv",
            status=ImportBatch.Status.RECEBIDO,
            imported_at=timezone.now(),
        )
        Transaction.objects.create(
            import_batch=batch,
            account=self.account_a,
            transaction_date=date(2026, 3, 10),
            description_raw="Compra mercado",
            description_norm="compra mercado",
            merchant_norm="mercado",
            amount="85.20",
            direction=Transaction.Direction.DEBITO,
            raw_hash="batch-has-transactions",
        )

        batch.account = self.account_b
        with self.assertRaises(ValidationError) as ctx:
            batch.save()

        self.assertIn("account", ctx.exception.message_dict)
