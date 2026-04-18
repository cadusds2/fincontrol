"""Fachada para regras deterministicas do MVP."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from classification.models import Category
from classification.services.yaml_rules import aplicar_regras_yaml
from transactions.models import Transaction


@dataclass(frozen=True)
class ResultadoRegra:
    """Resultado de uma regra determinística do MVP."""

    categoria: Category
    confianca: Decimal


def aplicar_regras_deterministicas(transacao: Transaction) -> ResultadoRegra | None:
    """Retorna classificacao por ruleset YAML ativo ou `None` sem match."""

    resultado = aplicar_regras_yaml(transacao)
    if resultado is not None:
        return ResultadoRegra(categoria=resultado.categoria, confianca=resultado.confianca)

    return None
