"""Analisa merchant_norm em CSVs sem persistir dados."""

from __future__ import annotations

import csv
import io
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from imports.parsers import MAPA_PARSERS
from imports.services.normalization import (
    MERCHANTS_TECNICOS_ESTAVEIS,
    normalizar_descricao_e_extrair_merchant,
)


@dataclass
class GrupoMerchant:
    total: int = 0
    direcoes: Counter[str] = field(default_factory=Counter)
    exemplos: set[str] = field(default_factory=set)
    sensivel: bool = False


class Command(BaseCommand):
    help = "Analisa merchant_norm em CSVs suportados sem gravar MerchantMap, Transaction ou ImportBatch."

    def add_arguments(self, parser):
        parser.add_argument("arquivos", nargs="+", help="Caminhos dos CSVs a analisar.")
        parser.add_argument(
            "--file-type",
            required=True,
            choices=sorted(MAPA_PARSERS.keys()),
            help="Tipo de arquivo explicito do parser dedicado.",
        )

    def handle(self, *args, **options):
        file_type = options["file_type"]
        parser = MAPA_PARSERS[file_type]
        arquivos = [Path(caminho) for caminho in options["arquivos"]]
        grupos: dict[str, GrupoMerchant] = defaultdict(GrupoMerchant)
        linhas_total = 0
        linhas_invalidas = 0

        for caminho in arquivos:
            if not caminho.exists():
                raise CommandError(f"Arquivo nao encontrado: {caminho}")

            conteudo_csv = _ler_conteudo_csv(caminho)
            leitor = csv.DictReader(io.StringIO(conteudo_csv))

            try:
                parser.validar_cabecalho(leitor.fieldnames)
            except ValueError as erro:
                raise CommandError(f"{caminho}: {erro}") from erro

            for indice, linha_csv in enumerate(leitor, start=1):
                linhas_total += 1
                try:
                    linha = parser.interpretar_linha(linha_csv)
                    descricao = normalizar_descricao_e_extrair_merchant(linha.descricao_bruta)
                except Exception as erro:  # noqa: BLE001
                    linhas_invalidas += 1
                    self.stderr.write(f"{caminho.name}: linha {indice} ignorada: {erro}")
                    continue

                grupo = grupos[descricao.merchant_norm]
                grupo.total += 1
                grupo.direcoes[linha.direcao] += 1
                grupo.exemplos.add(_mascarar_exemplo(descricao.description_norm))
                if _descricao_potencialmente_sensivel(descricao.description_norm):
                    grupo.sensivel = True

        self.stdout.write(f"Linhas analisadas: {linhas_total}")
        self.stdout.write(f"Linhas invalidas: {linhas_invalidas}")
        self.stdout.write(f"Merchants unicos: {len(grupos)}")
        self.stdout.write("")
        self.stdout.write("qtd\tdirecoes\tsugestao\tmerchant_norm\texemplo_mascarado")

        for merchant_norm, grupo in sorted(
            grupos.items(),
            key=lambda item: (-item[1].total, item[0]),
        ):
            sugestao = _sugerir_acao(merchant_norm, grupo)
            direcoes = ",".join(f"{direcao}:{total}" for direcao, total in sorted(grupo.direcoes.items()))
            exemplo = sorted(grupo.exemplos)[0] if grupo.exemplos else "<sem exemplo>"
            merchant_para_saida = (
                "<contraparte_transferencia_pix>"
                if grupo.sensivel and sugestao == "revisar_sem_merchant_map"
                else merchant_norm
            )
            self.stdout.write(
                f"{grupo.total}\t{direcoes}\t{sugestao}\t{merchant_para_saida}\t{exemplo}"
            )


def _ler_conteudo_csv(caminho: Path) -> str:
    dados = caminho.read_bytes()
    for encoding in ("utf-8-sig", "latin-1", "iso-8859-1"):
        try:
            return dados.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise CommandError(f"Nao foi possivel decodificar o arquivo: {caminho}")


def _mascarar_exemplo(description_norm: str) -> str:
    partes = [parte.strip() for parte in description_norm.split("-", 1)]
    if len(partes) == 2:
        return f"{partes[0]} - <valor_mascarado>"
    if description_norm in MERCHANTS_TECNICOS_ESTAVEIS:
        return description_norm
    return "<descricao_mascarada>"


def _descricao_potencialmente_sensivel(description_norm: str) -> bool:
    return "transferencia" in description_norm or "pix" in description_norm


def _sugerir_acao(merchant_norm: str, grupo: GrupoMerchant) -> str:
    if merchant_norm == "indefinido":
        return "revisar_normalizacao"
    if merchant_norm in MERCHANTS_TECNICOS_ESTAVEIS:
        return "tecnico_estavel"
    if merchant_norm == "ajuste de compra no debito":
        return "tecnico_estavel"
    if grupo.sensivel:
        return "revisar_sem_merchant_map"
    if grupo.total >= 2:
        return "candidato_merchant_map"
    return "amostra_unica"
