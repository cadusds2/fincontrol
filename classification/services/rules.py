"""Regras determinísticas do MVP para classificação de transações.

Observação: esta estrutura foi mantida deliberadamente simples em Python para o MVP.
No futuro, pode migrar para regras declarativas em YAML sem alterar o contrato do serviço.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from classification.models import Category
from transactions.models import Transaction


@dataclass(frozen=True)
class ResultadoRegra:
    """Resultado de uma regra determinística do MVP."""

    categoria: Category
    confianca: Decimal


def aplicar_regras_deterministicas(transacao: Transaction) -> ResultadoRegra | None:
    """Retorna classificação por regras de alta confiança ou `None` sem match."""

    texto_base = " ".join(
        [
            (transacao.description_norm or "").casefold(),
            (transacao.merchant_norm or "").casefold(),
        ]
    )

    categoria_pagamento_fatura = _buscar_categoria_tecnica("pagamento-de-fatura")
    if categoria_pagamento_fatura and _contem_termos(texto_base, ("pagamento", "fatura")):
        return ResultadoRegra(categoria=categoria_pagamento_fatura, confianca=Decimal("0.95"))

    categoria_transferencia_interna = _buscar_categoria_tecnica("transferencia-interna")
    if categoria_transferencia_interna and (
        _contem_termos(texto_base, ("transferencia", "interna"))
        or _contem_termos(texto_base, ("transferencia", "entre", "contas"))
        or _contem_termos(texto_base, ("pix", "propria"))
    ):
        return ResultadoRegra(categoria=categoria_transferencia_interna, confianca=Decimal("0.95"))

    categoria_movimentacao_investimentos = _buscar_categoria_tecnica("movimentacao-de-investimentos")
    if categoria_movimentacao_investimentos and (
        _contem_termos(texto_base, ("movimentacao", "investimentos"))
        or _contem_termos(texto_base, ("resgate", "investimento"))
        or _contem_termos(texto_base, ("aplicacao", "investimento"))
    ):
        return ResultadoRegra(categoria=categoria_movimentacao_investimentos, confianca=Decimal("0.95"))

    return None


def _buscar_categoria_tecnica(slug: str) -> Category | None:
    return Category.objects.filter(slug=slug, kind=Category.Kind.TECNICA, is_active=True).first()


def _contem_termos(texto: str, termos: tuple[str, ...]) -> bool:
    return all(termo in texto for termo in termos)
