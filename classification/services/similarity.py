"""Similaridade fuzzy para fallback de classificacao por MerchantMap."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db.models import QuerySet
from rapidfuzz import fuzz

from classification.models import Category, MerchantMap
from transactions.models import Transaction


DEFAULT_AUTO_THRESHOLD = 90
DEFAULT_REVIEW_THRESHOLD = 80


@dataclass(frozen=True)
class ResultadoSimilaridade:
    """Melhor resultado de similaridade encontrado para uma transacao."""

    category: Category | None
    merchant_map: MerchantMap | None
    score: Decimal
    action: str


def buscar_similaridade_fuzzy(transacao: Transaction) -> ResultadoSimilaridade | None:
    """Compara merchant_norm com MerchantMap e decide auto, review ou conflito."""

    merchant = _normalizar(transacao.merchant_norm)
    if not merchant:
        return None

    candidatos = list(_merchant_maps_elegiveis())
    if not candidatos:
        return None

    scored = [
        (
            _score(merchant, _normalizar(candidato.merchant_norm)),
            candidato,
        )
        for candidato in candidatos
        if _normalizar(candidato.merchant_norm)
    ]
    scored = [(score, candidato) for score, candidato in scored if score > Decimal("0")]
    if not scored:
        return None

    top_score = max(score for score, _ in scored)
    review_threshold = _threshold("CLASSIFICACAO_FUZZY_REVIEW_THRESHOLD", DEFAULT_REVIEW_THRESHOLD)
    if top_score < review_threshold:
        return None

    top_candidates = [candidato for score, candidato in scored if score == top_score]
    escolhido = _escolher_candidato(top_candidates)
    if _ha_empate_final_com_categorias_diferentes(top_candidates, escolhido):
        return ResultadoSimilaridade(
            category=None,
            merchant_map=None,
            score=top_score,
            action="conflict",
        )

    auto_threshold = _threshold("CLASSIFICACAO_FUZZY_AUTO_THRESHOLD", DEFAULT_AUTO_THRESHOLD)
    action = "auto" if top_score >= auto_threshold else "review"
    return ResultadoSimilaridade(
        category=escolhido.category,
        merchant_map=escolhido,
        score=top_score,
        action=action,
    )


def score_para_confianca(score: Decimal) -> Decimal:
    """Converte score 0-100 em confidence 0.00-1.00."""

    return (score / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _merchant_maps_elegiveis() -> QuerySet[MerchantMap]:
    return (
        MerchantMap.objects.select_related("category")
        .filter(
            category__is_active=True,
            category__kind=Category.Kind.CONSUMO,
            category__is_reportable=True,
        )
    )


def _score(valor: str, candidato: str) -> Decimal:
    score_float = fuzz.token_set_ratio(valor, candidato)
    return Decimal(str(score_float)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _escolher_candidato(candidatos: list[MerchantMap]) -> MerchantMap:
    return sorted(
        candidatos,
        key=lambda item: (
            -item.usage_count,
            -(item.confidence or Decimal("0")),
            -(item.updated_at.timestamp() if item.updated_at else 0),
            item.id,
        ),
    )[0]


def _ha_empate_final_com_categorias_diferentes(
    candidatos: list[MerchantMap],
    escolhido: MerchantMap,
) -> bool:
    empatados = [
        candidato
        for candidato in candidatos
        if (
            candidato.usage_count == escolhido.usage_count
            and (candidato.confidence or Decimal("0")) == (escolhido.confidence or Decimal("0"))
            and candidato.updated_at == escolhido.updated_at
        )
    ]
    categorias = {candidato.category_id for candidato in empatados}
    return len(categorias) > 1


def _threshold(setting_name: str, default: int) -> Decimal:
    value = getattr(settings, setting_name, default)
    return Decimal(str(value))


def _normalizar(value: str) -> str:
    return " ".join((value or "").casefold().split())
