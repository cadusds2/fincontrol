"""Serviço de importação CSV acionado pelo Django Admin."""

from __future__ import annotations

import csv
import hashlib
import io
from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction

from imports.models import ImportBatch
from imports.parsers import MAPA_PARSERS
from imports.services.normalization import normalizar_descricao_e_extrair_merchant
from classification.services.classification_service import classificar_transacao
from transactions.models import Transaction


class ErroEstruturalArquivoCsv(Exception):
    """Erro para falhas estruturais do arquivo CSV."""


@dataclass
class ResultadoImportacao:
    linhas_total: int = 0
    linhas_importadas: int = 0
    linhas_puladas: int = 0
    linhas_duplicadas: int = 0
    erros_estruturais: list[str] | None = None
    erros_por_linha: list[str] | None = None
    erros_fatais: list[str] | None = None

    def __post_init__(self) -> None:
        if self.erros_estruturais is None:
            self.erros_estruturais = []
        if self.erros_por_linha is None:
            self.erros_por_linha = []
        if self.erros_fatais is None:
            self.erros_fatais = []

    @property
    def total_erros(self) -> int:
        return len(self.erros_estruturais) + len(self.erros_por_linha) + len(self.erros_fatais)


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
            raise ErroEstruturalArquivoCsv("Nenhum arquivo CSV foi anexado ao lote.")

        conteudo_csv = ler_conteudo_csv(lote)
        leitor = csv.DictReader(io.StringIO(conteudo_csv))
        try:
            parser.validar_cabecalho(leitor.fieldnames)
        except ValueError as erro_cabecalho:
            raise ErroEstruturalArquivoCsv(str(erro_cabecalho)) from erro_cabecalho

        for indice, linha_csv in enumerate(leitor, start=1):
            resultado.linhas_total += 1
            try:
                linha_canonica = parser.interpretar_linha(linha_csv)
                descricao_normalizada = normalizar_descricao_e_extrair_merchant(
                    linha_canonica.descricao_bruta
                )
                raw_hash = gerar_raw_hash(
                    account_id=lote.account_id,
                    data_transacao=linha_canonica.data_transacao.isoformat(),
                    valor=linha_canonica.valor,
                    descricao_norm=descricao_normalizada.description_norm,
                )
                external_id = normalizar_external_id(linha_canonica.external_id)

                if transacao_ja_importada(
                    account_id=lote.account_id,
                    external_id=external_id,
                    raw_hash=raw_hash,
                ):
                    resultado.linhas_duplicadas += 1
                    resultado.linhas_puladas += 1
                    continue

                with transaction.atomic():
                    transacao = Transaction.objects.create(
                        import_batch=lote,
                        account=lote.account,
                        transaction_date=linha_canonica.data_transacao,
                        posted_date=linha_canonica.data_competencia,
                        description_raw=linha_canonica.descricao_bruta,
                        description_norm=descricao_normalizada.description_norm,
                        merchant_raw=descricao_normalizada.merchant_raw,
                        merchant_norm=descricao_normalizada.merchant_norm,
                        amount=linha_canonica.valor,
                        currency=linha_canonica.moeda,
                        direction=linha_canonica.direcao,
                        external_id=external_id,
                        raw_hash=raw_hash,
                        classification_source=Transaction.ClassificationSource.UNCLASSIFIED,
                    )
                    classificar_transacao(transacao)

                resultado.linhas_importadas += 1
            except Exception as erro_linha:  # noqa: BLE001
                resultado.linhas_puladas += 1
                resultado.erros_por_linha.append(f"Linha {indice}: {erro_linha}")

    except ErroEstruturalArquivoCsv as erro_estrutural:
        resultado.erros_estruturais.append(str(erro_estrutural))
    except Exception as erro_fatal:  # noqa: BLE001
        resultado.erros_fatais.append(f"Erro fatal inesperado: {erro_fatal}")

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

    houve_erro_estrutural = bool(resultado.erros_estruturais)
    houve_erro_fatal = bool(resultado.erros_fatais)
    houve_erro_linha = bool(resultado.erros_por_linha)

    if houve_erro_estrutural or houve_erro_fatal:
        lote.status = ImportBatch.Status.FAILED
    elif resultado.linhas_total == 0:
        lote.status = ImportBatch.Status.FAILED
    elif resultado.linhas_importadas == 0 and resultado.linhas_duplicadas == resultado.linhas_total:
        lote.status = ImportBatch.Status.PARTIAL
    elif resultado.linhas_importadas == 0:
        lote.status = ImportBatch.Status.FAILED
    elif resultado.linhas_puladas > 0 or houve_erro_linha:
        lote.status = ImportBatch.Status.PARTIAL
    else:
        lote.status = ImportBatch.Status.PROCESSED

    lote.error_log = montar_error_log(resultado)
    lote.save()


def ler_conteudo_csv(lote: ImportBatch) -> str:
    """Lê o CSV do lote com tratamento simples de encoding e ponteiro."""

    lote.file.open("rb")
    try:
        if hasattr(lote.file, "seek"):
            lote.file.seek(0)
        dados_brutos = lote.file.read()
    finally:
        lote.file.close()

    for encoding in ("utf-8-sig", "latin-1", "iso-8859-1"):
        try:
            return dados_brutos.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ErroEstruturalArquivoCsv(
        "Não foi possível decodificar o arquivo CSV com os encodings suportados."
    )


def montar_error_log(resultado: ResultadoImportacao) -> str:
    linhas_erro: list[str] = []
    linhas_erro.extend(f"[estrutural] {erro}" for erro in resultado.erros_estruturais)
    linhas_erro.extend(f"[linha] {erro}" for erro in resultado.erros_por_linha)
    linhas_erro.extend(f"[fatal] {erro}" for erro in resultado.erros_fatais)
    return "\n".join(linhas_erro)


def gerar_raw_hash(account_id: int, data_transacao: str, valor: Decimal, descricao_norm: str) -> str:
    valor_normalizado = f"{valor:.2f}"
    carga = f"{account_id}|{data_transacao}|{valor_normalizado}|{descricao_norm}"
    return hashlib.sha256(carga.encode("utf-8")).hexdigest()


def normalizar_external_id(external_id: str | None) -> str | None:
    """Normaliza identificador externo para uso canônico de deduplicação."""

    texto = (external_id or "").strip()
    return texto or None


def transacao_ja_importada(account_id: int, external_id: str | None, raw_hash: str) -> bool:
    """Aplica regra de deduplicação priorizando identificador externo confiável."""

    if external_id:
        return Transaction.objects.filter(account_id=account_id, external_id=external_id).exists()
    return Transaction.objects.filter(account_id=account_id, raw_hash=raw_hash).exists()
