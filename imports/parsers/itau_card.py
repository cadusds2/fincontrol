"""Parser para `fatura_cartao_itau`."""

from __future__ import annotations

from .base import ParserCsvBase, LinhaCanonica, inferir_direcao_por_valor, parse_data, parse_decimal


class ParserItauCartao(ParserCsvBase):
    colunas_obrigatorias = ("data_compra", "descricao", "valor")

    def interpretar_linha(self, linha_csv: dict[str, str]) -> LinhaCanonica:
        data = parse_data(linha_csv.get("data_compra") or linha_csv.get("data"))
        descricao = (linha_csv.get("descricao") or linha_csv.get("estabelecimento") or "").strip()
        valor = parse_decimal(linha_csv.get("valor") or linha_csv.get("valor_compra"))
        direcao = inferir_direcao_por_valor(valor)
        return LinhaCanonica(
            data_transacao=data,
            descricao_bruta=descricao,
            valor=abs(valor),
            direcao=direcao,
        )
