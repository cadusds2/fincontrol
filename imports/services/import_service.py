"""Serviço de importação CSV acionado pelo Django Admin."""

from __future__ import annotations

import csv
import hashlib
import io
import unicodedata
from dataclasses import dataclass

from django.db import transaction

from imports.models import ImportBatch
from imports.parsers import MAPA_PARSERS
from transactions.models import Transaction


@dataclass
class ResultadoImportacao:
    linhas_total: int = 0
    linhas_importadas: int = 0
    linhas_puladas: int = 0
    linhas_duplicadas: int = 0
    erros: list[str] | None = None

    def __post_init__(self) -> None:
        if self.erros is None:
            self.erros = []


def executar_importacao_import_batch(import_batch_id: int) -> ResultadoImportacao:
    """Executa o pipeline de ingestão para um lote de importação."""

    lote = ImportBatch.objects.select_related("account").get(pk=import_batch_id)
    resultado = ResultadoImportacao()

    parser = MAPA_PARSERS.get(lote.file_type)
    if parser is None:
        lote.status = ImportBatch.Status.FAILED
        lote.error_log = f"Tipo de arquivo não suportado: {lote.file_type}"
        lote.save(update_fields=["status", "error_log", "updated_at"])
        return resultado

    lote.status = ImportBatch.Status.RECEIVED
    lote.save(update_fields=["status", "updated_at"])

    try:
        if not lote.file:
            raise ValueError("Nenhum arquivo CSV foi anexado ao lote.")

        dados_csv = lote.file.read()
        leitor = csv.DictReader(io.StringIO(dados_csv.decode("utf-8-sig")))
        parser.validar_cabecalho(leitor.fieldnames)

        for indice, linha_csv in enumerate(leitor, start=1):
            resultado.linhas_total += 1
            try:
                linha_canonica = parser.interpretar_linha(linha_csv)
                descricao_normalizada = normalizar_texto(linha_canonica.descricao_bruta)
                merchant_normalizado = extrair_merchant(descricao_normalizada)
                raw_hash = gerar_raw_hash(
                    account_id=lote.account_id,
                    data_transacao=linha_canonica.data_transacao.isoformat(),
                    valor=str(linha_canonica.valor),
                    descricao_norm=descricao_normalizada,
                )

                if Transaction.objects.filter(account=lote.account, raw_hash=raw_hash).exists():
                    resultado.linhas_duplicadas += 1
                    resultado.linhas_puladas += 1
                    continue

                with transaction.atomic():
                    Transaction.objects.create(
                        import_batch=lote,
                        account=lote.account,
                        transaction_date=linha_canonica.data_transacao,
                        posted_date=linha_canonica.data_competencia,
                        description_raw=linha_canonica.descricao_bruta,
                        description_norm=descricao_normalizada,
                        merchant_norm=merchant_normalizado,
                        amount=linha_canonica.valor,
                        currency=linha_canonica.moeda,
                        direction=linha_canonica.direcao,
                        raw_hash=raw_hash,
                        classification_source=Transaction.ClassificationSource.UNCLASSIFIED,
                    )

                resultado.linhas_importadas += 1
            except Exception as erro_linha:  # noqa: BLE001
                resultado.linhas_puladas += 1
                resultado.erros.append(f"Linha {indice}: {erro_linha}")

    except Exception as erro_geral:  # noqa: BLE001
        resultado.erros.append(f"Falha ao ler arquivo CSV: {erro_geral}")

    atualizar_status_lote(lote, resultado)
    return resultado


def atualizar_status_lote(lote: ImportBatch, resultado: ResultadoImportacao) -> None:
    """Atualiza os metadados finais do lote de importação."""

    lote.rows_total = resultado.linhas_total
    lote.rows_imported = resultado.linhas_importadas
    lote.rows_skipped = resultado.linhas_puladas
    lote.total_rows = resultado.linhas_total
    lote.imported_rows = resultado.linhas_importadas
    lote.duplicated_rows = resultado.linhas_duplicadas

    if resultado.erros and resultado.linhas_importadas == 0:
        lote.status = ImportBatch.Status.FAILED
    elif resultado.linhas_importadas == 0 and resultado.linhas_total > 0:
        lote.status = ImportBatch.Status.FAILED
    elif resultado.linhas_puladas > 0:
        lote.status = ImportBatch.Status.PARTIAL
    else:
        lote.status = ImportBatch.Status.PROCESSED

    lote.error_log = "\n".join(resultado.erros or [])
    lote.save()


def normalizar_texto(texto: str) -> str:
    texto_limpo = unicodedata.normalize("NFKD", texto or "")
    texto_limpo = "".join(char for char in texto_limpo if not unicodedata.combining(char))
    texto_limpo = " ".join(texto_limpo.lower().split())
    return texto_limpo


def extrair_merchant(descricao_normalizada: str) -> str:
    return " ".join(descricao_normalizada.split()[:3]).strip() or "indefinido"


def gerar_raw_hash(account_id: int, data_transacao: str, valor: str, descricao_norm: str) -> str:
    carga = f"{account_id}|{data_transacao}|{valor}|{descricao_norm}"
    return hashlib.sha256(carga.encode("utf-8")).hexdigest()
