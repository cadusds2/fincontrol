"""Parser para `extrato_conta_nubank`."""

from __future__ import annotations

from .base import ParserCsvBase, LinhaCanonica, inferir_direcao_por_valor, parse_data, parse_decimal


class ParserNubankConta(ParserCsvBase):
    colunas_obrigatorias = ("Data", "Valor", "Descrição")

    def interpretar_linha(self, linha_csv: dict[str, str]) -> LinhaCanonica:
        data = parse_data(
            self.obter_valor_coluna(linha_csv, "Data", "date", "data")
        )
        descricao = (
            self.obter_valor_coluna(linha_csv, "Descrição", "Descricao", "title", "descricao")
            or ""
        ).strip()
        valor = parse_decimal(
            self.obter_valor_coluna(linha_csv, "Valor", "amount", "valor")
        )
        identificador_externo = self.obter_valor_coluna(
            linha_csv,
            "Identificador",
            "identifier",
            "id",
        )
        direcao = inferir_direcao_por_valor(valor)
        return LinhaCanonica(
            data_transacao=data,
            descricao_bruta=descricao,
            valor=abs(valor),
            direcao=direcao,
            external_id=(identificador_externo or "").strip() or None,
        )
