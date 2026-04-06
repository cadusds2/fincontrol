"""Testes do app imports."""

from datetime import date

from django.core.files.base import ContentFile
from django.test import TestCase

from accounts.models import Account
from imports.models import ImportBatch
from imports.parsers.nubank_account import ParserNubankConta
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

    def criar_lote(
        self,
        conteudo_csv: str,
        file_type: str = ImportBatch.FileType.EXTRATO_CONTA_NUBANK,
    ) -> ImportBatch:
        lote = ImportBatch.objects.create(
            account=self.conta,
            file_type=file_type,
            reference_month=date(2026, 4, 1),
            source_filename="extrato.csv",
        )
        lote.file.save("extrato.csv", ContentFile(conteudo_csv.encode("utf-8")))
        lote.save()
        return lote

    def test_importacao_basica_preenche_campos_canonicos(self) -> None:
        csv_valido = (
            "Data,Valor,Identificador,Descrição\n"
            "10/03/2026,-10.50,abc123,  Compra no crédito   Café São José 123  \n"
        )
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
        self.assertEqual(transacao.external_id, "abc123")
        self.assertTrue(transacao.raw_hash)

    def test_importa_e_deduplica_transacoes_por_raw_hash(self) -> None:
        csv_valido = (
            "data_lancamento,descricao,valor\n"
            "10/03/2026,Cafe da esquina,-10.50\n"
        )
        lote_1 = self.criar_lote(
            csv_valido,
            file_type=ImportBatch.FileType.EXTRATO_CONTA_ITAU,
        )

        resultado_1 = executar_importacao_import_batch(lote_1.id)

        self.assertEqual(resultado_1.linhas_importadas, 1)
        self.assertEqual(Transaction.objects.count(), 1)

        lote_2 = self.criar_lote(
            csv_valido,
            file_type=ImportBatch.FileType.EXTRATO_CONTA_ITAU,
        )
        resultado_2 = executar_importacao_import_batch(lote_2.id)
        lote_2.refresh_from_db()

        self.assertEqual(resultado_2.linhas_total, 1)
        self.assertEqual(resultado_2.linhas_importadas, 0)
        self.assertEqual(resultado_2.linhas_puladas, 1)
        self.assertEqual(resultado_2.linhas_duplicadas, 1)
        self.assertEqual(lote_2.status, ImportBatch.Status.PARTIAL)
        self.assertEqual(Transaction.objects.count(), 1)

    def test_importa_duas_transacoes_iguais_com_external_id_diferente(self) -> None:
        csv_valido = (
            "Data,Valor,Identificador,Descrição\n"
            "10/01/2025,-28.00,id_1,Compra no débito - Casa do Nando\n"
            "10/01/2025,-28.00,id_2,Compra no débito - Casa do Nando\n"
        )
        lote = self.criar_lote(csv_valido)

        resultado = executar_importacao_import_batch(lote.id)

        self.assertEqual(resultado.linhas_total, 2)
        self.assertEqual(resultado.linhas_importadas, 2)
        self.assertEqual(resultado.linhas_duplicadas, 0)
        self.assertEqual(Transaction.objects.count(), 2)
        self.assertSetEqual(
            set(Transaction.objects.values_list("external_id", flat=True)),
            {"id_1", "id_2"},
        )

    def test_nao_duplica_quando_external_id_e_raw_hash_ja_existirem(self) -> None:
        csv_valido = (
            "Data,Valor,Identificador,Descrição\n"
            "10/01/2025,-28.00,id_1,Compra no débito - Casa do Nando\n"
        )
        lote_1 = self.criar_lote(csv_valido)
        resultado_1 = executar_importacao_import_batch(lote_1.id)
        self.assertEqual(resultado_1.linhas_importadas, 1)

        lote_2 = self.criar_lote(csv_valido)
        resultado_2 = executar_importacao_import_batch(lote_2.id)

        self.assertEqual(resultado_2.linhas_importadas, 0)
        self.assertEqual(resultado_2.linhas_duplicadas, 1)
        self.assertEqual(Transaction.objects.count(), 1)

    def test_importa_pares_de_mesmo_external_id_com_raw_hash_diferente(self) -> None:
        csv_valido = (
            "Data,Valor,Identificador,Descrição\n"
            "03/04/2025,-79.00,67eec87e-b9f2-4538-a9b2-29c95bf166c2,Pagamento de fatura\n"
            "03/04/2025,79.00,67eec87e-b9f2-4538-a9b2-29c95bf166c2,Estorno pagamento de fatura\n"
            "03/04/2025,-60.00,67eec84c-43f3-45b8-893c-c164d40b645e,Transferência enviada pelo Pix - CARLOS\n"
            "03/04/2025,60.00,67eec84c-43f3-45b8-893c-c164d40b645e,Transferência recebida pelo Pix - CARLOS\n"
            "03/04/2025,-15.90,abc123-def456-ghi789-jkl000,Compra no débito - Padaria São José\n"
            "03/04/2025,15.90,abc123-def456-ghi789-jkl000,Estorno compra no débito - Padaria São José\n"
        )
        lote = self.criar_lote(csv_valido)

        resultado = executar_importacao_import_batch(lote.id)
        transacoes = Transaction.objects.order_by("external_id", "id")

        self.assertEqual(resultado.linhas_total, 6)
        self.assertEqual(resultado.linhas_importadas, 6)
        self.assertEqual(resultado.linhas_duplicadas, 0)
        self.assertEqual(transacoes.count(), 6)
        self.assertEqual(
            transacoes.values("external_id").distinct().count(),
            3,
        )
        self.assertEqual(
            transacoes.filter(external_id="67eec87e-b9f2-4538-a9b2-29c95bf166c2").count(),
            2,
        )
        self.assertEqual(
            transacoes.filter(external_id="67eec84c-43f3-45b8-893c-c164d40b645e").count(),
            2,
        )
        self.assertEqual(
            transacoes.filter(external_id="abc123-def456-ghi789-jkl000").count(),
            2,
        )
        self.assertEqual(transacoes.values("raw_hash").distinct().count(), 6)

    def test_linha_sem_identificador_no_nubank_conta_rejeitada_sem_duplicidade(self) -> None:
        csv_invalido = (
            "Data,Valor,Identificador,Descrição\n"
            "10/03/2026,-10.50,   ,Cafe da esquina\n"
        )
        lote = self.criar_lote(csv_invalido)

        resultado = executar_importacao_import_batch(lote.id)
        lote.refresh_from_db()

        self.assertEqual(resultado.linhas_total, 1)
        self.assertEqual(resultado.linhas_importadas, 0)
        self.assertEqual(resultado.linhas_puladas, 1)
        self.assertEqual(resultado.linhas_duplicadas, 0)
        self.assertEqual(lote.status, ImportBatch.Status.FAILED)
        self.assertIn("Linha 1: Identificador obrigatório ausente ou vazio", lote.error_log)
        self.assertEqual(Transaction.objects.count(), 0)

    def test_falha_quando_cabecalho_ausente(self) -> None:
        csv_invalido = "data,descricao,valor\n2026-03-11,Despesa totalmente nova,-25.00\n"
        lote = self.criar_lote(csv_invalido)

        resultado = executar_importacao_import_batch(lote.id)
        lote.refresh_from_db()

        self.assertEqual(resultado.linhas_importadas, 0)
        self.assertEqual(lote.status, ImportBatch.Status.FAILED)
        self.assertIn("Colunas obrigatórias ausentes", lote.error_log)

    def test_importa_csv_com_fallback_latin_1(self) -> None:
        csv_latin_1 = (
            "Data,Valor,Identificador,Descrição\n"
            "12/03/2026,-15.90,abc123,Padaria São José\n"
        )
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
            "Data,Valor,Identificador,Descrição\n"
            "10/03/2026,-10.50,abc123,Cafe da esquina\n"
            "31-31-2026,-20.00,abc124,Linha invalida\n"
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

        csv_valido = (
            "Data,Valor,Identificador,Descrição\n"
            "10/03/2026,-10.50,abc123,Cafe da esquina\n"
        )
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


class ParserNubankContaTests(TestCase):
    def setUp(self) -> None:
        self.parser = ParserNubankConta()

    def test_valida_cabecalho_real_nubank_conta(self) -> None:
        self.parser.validar_cabecalho(["Data", "Valor", "Identificador", "Descrição"])

    def test_interpreta_linha_valor_positivo_como_credito(self) -> None:
        linha = self.parser.interpretar_linha(
            {
                "Data": "03/04/2025",
                "Valor": "60.00",
                "Identificador": "67eec84c-43f3-45b8-893c-c164d40b645e",
                "Descrição": "Transferência recebida pelo Pix - CARLOS",
            }
        )

        self.assertEqual(linha.data_transacao, date(2025, 4, 3))
        self.assertEqual(linha.valor, 60)
        self.assertEqual(linha.direcao, "credit")
        self.assertEqual(linha.descricao_bruta, "Transferência recebida pelo Pix - CARLOS")
        self.assertEqual(linha.external_id, "67eec84c-43f3-45b8-893c-c164d40b645e")

    def test_interpreta_linha_valor_negativo_como_debito(self) -> None:
        linha = self.parser.interpretar_linha(
            {
                "Data": "03/04/2025",
                "Valor": "-79.00",
                "Identificador": "67eec87e-b9f2-4538-a9b2-29c95bf166c2",
                "Descrição": "Pagamento de fatura",
            }
        )

        self.assertEqual(linha.data_transacao, date(2025, 4, 3))
        self.assertEqual(linha.valor, 79)
        self.assertEqual(linha.direcao, "debit")
        self.assertEqual(linha.descricao_bruta, "Pagamento de fatura")
        self.assertEqual(linha.external_id, "67eec87e-b9f2-4538-a9b2-29c95bf166c2")

    def test_rejeita_linha_com_identificador_vazio(self) -> None:
        with self.assertRaisesMessage(
            ValueError,
            "Identificador obrigatório ausente ou vazio no layout Nubank conta.",
        ):
            self.parser.interpretar_linha(
                {
                    "Data": "03/04/2025",
                    "Valor": "-79.00",
                    "Identificador": "   ",
                    "Descrição": "Pagamento de fatura",
                }
            )
