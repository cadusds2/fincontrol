from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from accounts.models import Account
from imports.models import ImportBatch
from transactions.models import Transaction


class TransactionModelTests(TestCase):
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
        self.batch_account_a = ImportBatch.objects.create(
            account=self.account_a,
            file_type=ImportBatch.TipoArquivo.EXTRATO_CONTA_NUBANK,
            source_filename="extrato.csv",
            status=ImportBatch.Status.RECEBIDO,
            imported_at=timezone.now(),
        )

    def test_clean_rejects_account_mismatch_with_import_batch(self) -> None:
        transaction = Transaction(
            import_batch=self.batch_account_a,
            account=self.account_b,
            transaction_date=timezone.now().date(),
            description_raw="Compra padaria",
            description_norm="compra padaria",
            merchant_norm="padaria",
            amount="10.00",
            direction=Transaction.Direction.DEBITO,
            raw_hash="abc123",
        )

        with self.assertRaises(ValidationError):
            transaction.clean()

    def test_save_rejects_account_mismatch_with_import_batch(self) -> None:
        with self.assertRaises(ValidationError):
            Transaction.objects.create(
                import_batch=self.batch_account_a,
                account=self.account_b,
                transaction_date=timezone.now().date(),
                description_raw="Compra mercado",
                description_norm="compra mercado",
                merchant_norm="mercado",
                amount="25.00",
                direction=Transaction.Direction.DEBITO,
                raw_hash="def456",
            )

    def test_save_allows_matching_account_and_import_batch(self) -> None:
        transaction = Transaction.objects.create(
            import_batch=self.batch_account_a,
            account=self.account_a,
            transaction_date=timezone.now().date(),
            description_raw="Compra farmácia",
            description_norm="compra farmacia",
            merchant_norm="farmacia",
            amount="30.00",
            direction=Transaction.Direction.DEBITO,
            raw_hash="ghi789",
        )

        self.assertEqual(transaction.account_id, self.batch_account_a.account_id)

    def test_save_rejects_nonexistent_import_batch_with_validation_error(self) -> None:
        with self.assertRaises(ValidationError) as ctx:
            Transaction.objects.create(
                import_batch_id=999999,
                account=self.account_a,
                transaction_date=timezone.now().date(),
                description_raw="Compra inválida",
                description_norm="compra invalida",
                merchant_norm="invalida",
                amount="11.00",
                direction=Transaction.Direction.DEBITO,
                raw_hash="nonexistent-batch",
            )

        self.assertIn("import_batch", ctx.exception.message_dict)

    def test_create_rejects_non_unclassified_source(self) -> None:
        with self.assertRaises(ValidationError) as ctx:
            Transaction.objects.create(
                import_batch=self.batch_account_a,
                account=self.account_a,
                transaction_date=timezone.now().date(),
                description_raw="Compra criada como manual",
                description_norm="compra criada como manual",
                merchant_norm="mercado",
                amount="25.00",
                direction=Transaction.Direction.DEBITO,
                raw_hash="manual-on-create",
                classification_source=Transaction.ClassificationSource.MANUAL,
            )

        self.assertIn("classification_source", ctx.exception.message_dict)

    def test_update_allows_transition_from_unclassified_to_manual(self) -> None:
        transaction = Transaction.objects.create(
            import_batch=self.batch_account_a,
            account=self.account_a,
            transaction_date=timezone.now().date(),
            description_raw="Compra para classificar",
            description_norm="compra para classificar",
            merchant_norm="padaria",
            amount="42.00",
            direction=Transaction.Direction.DEBITO,
            raw_hash="unclassified-then-manual",
        )

        transaction.classification_source = Transaction.ClassificationSource.MANUAL
        transaction.save()

        self.assertEqual(transaction.classification_source, Transaction.ClassificationSource.MANUAL)
