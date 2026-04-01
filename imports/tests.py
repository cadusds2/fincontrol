"""Testes do app imports."""

from datetime import date

from django.core.files.base import ContentFile
from django.test import TestCase

from accounts.models import Account
from imports.models import ImportBatch
from imports.services.import_service import executar_importacao_import_batch
from transactions.models import Transaction


class ImportacaoCsvServiceTests(TestCase):
    def setUp(self) -> None:
        self.conta = Account.objects.create(
            bank_name="Nubank",
            account_type=Account.AccountType.CHECKING,
            display_name="Conta principal",
        )

    def criar_lote(self, conteudo_csv: str) -> ImportBatch:
        lote = ImportBatch.objects.create(
            account=self.conta,
            file_type=ImportBatch.FileType.EXTRATO_CONTA_NUBANK,
            reference_month=date(2026, 4, 1),
            source_filename="extrato.csv",
        )
        lote.file.save("extrato.csv", ContentFile(conteudo_csv.encode("utf-8")))
        lote.save()
        return lote

    def test_importa_e_deduplica_transacoes_por_raw_hash(self) -> None:
        csv_valido = "date,title,amount\n2026-03-10,Cafe da esquina,-10.50\n"
        lote_1 = self.criar_lote(csv_valido)

        resultado_1 = executar_importacao_import_batch(lote_1.id)

        self.assertEqual(resultado_1.linhas_importadas, 1)
        self.assertEqual(Transaction.objects.count(), 1)

        lote_2 = self.criar_lote(csv_valido)
        resultado_2 = executar_importacao_import_batch(lote_2.id)

        self.assertEqual(resultado_2.linhas_duplicadas, 1)
        self.assertEqual(Transaction.objects.count(), 1)

    def test_falha_quando_cabecalho_ausente(self) -> None:
        csv_invalido = "data,descricao,valor\n2026-03-11,Despesa totalmente nova,-25.00\n"
        lote = self.criar_lote(csv_invalido)

        resultado = executar_importacao_import_batch(lote.id)
        lote.refresh_from_db()

        self.assertEqual(resultado.linhas_importadas, 0)
        self.assertEqual(lote.status, ImportBatch.Status.FAILED)
        self.assertIn("Colunas obrigatórias ausentes", lote.error_log)
