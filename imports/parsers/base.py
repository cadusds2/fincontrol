"""Contrato e utilitários base para parsers de CSV do app imports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass
class LinhaCanonica:
    """Representa uma linha de transação convertida para formato canônico."""

    data_transacao: date
    descricao_bruta: str
    valor: Decimal
    direcao: str
    external_id: str | None = None
    data_competencia: date | None = None
    moeda: str = "BRL"


class ParserCsvBase:
    """Contrato mínimo para parsers dedicados por tipo de arquivo no MVP."""

    colunas_obrigatorias: tuple[str, ...] = ()

    @staticmethod
    def normalizar_nome_coluna(coluna: str) -> str:
        return (coluna or "").strip().lower()

    def validar_cabecalho(self, colunas: list[str] | None) -> None:
        if not colunas:
            raise ValueError("Arquivo CSV sem cabeçalho.")

        colunas_presentes = {
            self.normalizar_nome_coluna(coluna)
            for coluna in colunas
            if self.normalizar_nome_coluna(coluna)
        }
        colunas_faltantes = [
            coluna
            for coluna in self.colunas_obrigatorias
            if self.normalizar_nome_coluna(coluna) not in colunas_presentes
        ]
        if colunas_faltantes:
            raise ValueError(
                "Colunas obrigatórias ausentes: " + ", ".join(colunas_faltantes)
            )

    def obter_valor_coluna(self, linha_csv: dict[str, str], *alternativas: str) -> str | None:
        mapa_normalizado = {
            self.normalizar_nome_coluna(chave): valor for chave, valor in (linha_csv or {}).items()
        }
        for alternativa in alternativas:
            valor = mapa_normalizado.get(self.normalizar_nome_coluna(alternativa))
            if valor not in (None, ""):
                return valor
        return None

    def interpretar_linha(self, linha_csv: dict[str, str]) -> LinhaCanonica:  # pragma: no cover
        raise NotImplementedError


def parse_data(valor: str) -> date:
    """Converte texto para data aceitando formatos comuns de extrato."""

    texto = (valor or "").strip()
    for formato in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    raise ValueError(f"Data inválida: {texto}")


def parse_decimal(valor: str) -> Decimal:
    """Converte texto monetário brasileiro para Decimal."""

    texto = (valor or "").strip().replace("R$", "").replace(" ", "")
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    return Decimal(texto)


def inferir_direcao_por_valor(valor: Decimal) -> str:
    """Define direção da transação com base no sinal do valor."""

    return "debit" if valor < 0 else "credit"
