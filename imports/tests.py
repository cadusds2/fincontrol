"""Testes do app imports."""

from datetime import date

from django.core.files.base import ContentFile
from django.test import TestCase

from accounts.models import Account
from imports.models import ImportBatch
from imports.services.import_service import executar_importacao_import_batch
from imports.services.normalization import (
    extrair_merchant,
    normalizar_descricao_e_extrair_merchant,
    normalizar_texto,
)
from classification.models import Category, MerchantMap, ReviewQueue
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

    def test_importacao_basica_preenche_campos_canonicos(self) -> None:
        csv_valido = "date,title,amount\n2026-03-10,  Compra no crédito   Café São José 123  ,-10.50\n"
        lote = self.criar_lote(csv_valido)

        resultado = executar_importacao_import_batch(lote.id)
        lote.refresh_from_db()
        transacao = Transaction.objects.get()

        self.assertEqual(resultado.linhas_total, 1)
        self.assertEqual(resultado.linhas_importadas, 1)
        self.assertEqual(resultado.linhas_puladas, 0)
        self.assertEqual(resultado.linhas_duplicadas, 0)
        self.assertEqual(lote.status, ImportBatch.Status.PROCESSED)
        self.assertEqual(transacao.description_raw, "Compra no crédito   Café São José 123")
        self.assertEqual(transacao.description_norm, "compra no credito cafe sao jose 123")
        self.assertEqual(transacao.merchant_raw, "cafe sao jose 123")
        self.assertEqual(transacao.merchant_norm, "cafe sao jose 123")
        self.assertEqual(
            transacao.classification_source,
            Transaction.ClassificationSource.UNCLASSIFIED,
        )
        self.assertEqual(ReviewQueue.objects.filter(transaction=transacao).count(), 1)
        self.assertTrue(transacao.raw_hash)

    def test_importa_e_deduplica_transacoes_por_raw_hash(self) -> None:
        csv_valido = "date,title,amount\n2026-03-10,Cafe da esquina,-10.50\n"
        lote_1 = self.criar_lote(csv_valido)

        resultado_1 = executar_importacao_import_batch(lote_1.id)

        self.assertEqual(resultado_1.linhas_importadas, 1)
        self.assertEqual(Transaction.objects.count(), 1)

        lote_2 = self.criar_lote(csv_valido)
        resultado_2 = executar_importacao_import_batch(lote_2.id)
        lote_2.refresh_from_db()

        self.assertEqual(resultado_2.linhas_total, 1)
        self.assertEqual(resultado_2.linhas_importadas, 0)
        self.assertEqual(resultado_2.linhas_puladas, 1)
        self.assertEqual(resultado_2.linhas_duplicadas, 1)
        self.assertEqual(lote_2.status, ImportBatch.Status.PARTIAL)
        self.assertEqual(Transaction.objects.count(), 1)

    def test_falha_quando_cabecalho_ausente(self) -> None:
        csv_invalido = "data,descricao,valor\n2026-03-11,Despesa totalmente nova,-25.00\n"
        lote = self.criar_lote(csv_invalido)

        resultado = executar_importacao_import_batch(lote.id)
        lote.refresh_from_db()

        self.assertEqual(resultado.linhas_importadas, 0)
        self.assertEqual(lote.status, ImportBatch.Status.FAILED)
        self.assertIn("Colunas obrigatórias ausentes", lote.error_log)

    def test_importa_csv_com_fallback_latin_1(self) -> None:
        csv_latin_1 = "date,title,amount\n2026-03-12,Padaria São José,-15.90\n"
        lote = ImportBatch.objects.create(
            account=self.conta,
            file_type=ImportBatch.FileType.EXTRATO_CONTA_NUBANK,
            reference_month=date(2026, 4, 1),
            source_filename="extrato_latin1.csv",
        )
        lote.file.save("extrato_latin1.csv", ContentFile(csv_latin_1.encode("latin-1")))
        lote.save()

        resultado = executar_importacao_import_batch(lote.id)
        lote.refresh_from_db()

        self.assertEqual(resultado.linhas_importadas, 1)
        self.assertEqual(lote.status, ImportBatch.Status.PROCESSED)

    def test_lote_parcial_em_erro_por_linha(self) -> None:
        csv_parcial = (
            "date,title,amount\n"
            "2026-03-10,Cafe da esquina,-10.50\n"
            "31-31-2026,Linha invalida,-20.00\n"
        )
        lote = self.criar_lote(csv_parcial)

        resultado = executar_importacao_import_batch(lote.id)
        lote.refresh_from_db()

        self.assertEqual(resultado.linhas_importadas, 1)
        self.assertEqual(resultado.linhas_puladas, 1)
        self.assertEqual(lote.status, ImportBatch.Status.PARTIAL)
        self.assertIn("[linha] Linha 2", lote.error_log)


    def test_importacao_dispara_classificacao_por_merchant_map(self) -> None:
        categoria = Category.objects.create(
            name="Alimentação",
            slug="alimentacao",
            kind=Category.Kind.CONSUMO,
            is_reportable=True,
        )
        MerchantMap.objects.create(
            merchant_norm="cafe da esquina",
            category=categoria,
            source=MerchantMap.Source.SEED,
        )

        csv_valido = "date,title,amount\n2026-03-10,Cafe da esquina,-10.50\n"
        lote = self.criar_lote(csv_valido)

        resultado = executar_importacao_import_batch(lote.id)
        transacao = Transaction.objects.get()

        self.assertEqual(resultado.linhas_importadas, 1)
        self.assertEqual(transacao.category, categoria)
        self.assertEqual(transacao.classification_source, Transaction.ClassificationSource.MERCHANT_MAP)
        self.assertEqual(ReviewQueue.objects.filter(transaction=transacao).count(), 0)


class NormalizacaoImportacaoTests(TestCase):
    def test_normalizacao_basica_remove_acento_caixa_e_espaco(self) -> None:
        self.assertEqual(normalizar_texto("  DéBiTo   Mercado  São   José  "), "debito mercado sao jose")

    def test_extracao_merchant_remove_ruido_inicial(self) -> None:
        merchant_raw, merchant_norm = extrair_merchant("compra no credito padaria vila mariana 457")

        self.assertEqual(merchant_raw, "padaria vila mariana 457")
        self.assertEqual(merchant_norm, "padaria vila mariana 457")

    def test_fluxo_unificado_de_normalizacao(self) -> None:
        descricao = normalizar_descricao_e_extrair_merchant("Pix   Restaurante Sabor & Arte")

        self.assertEqual(descricao.description_norm, "pix restaurante sabor & arte")
        self.assertEqual(descricao.merchant_raw, "restaurante sabor & arte")
        self.assertEqual(descricao.merchant_norm, "restaurante sabor & arte")
