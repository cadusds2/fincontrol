"""Serviços de revisão manual para operação via Django Admin."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from classification.models import MerchantMap, ReviewQueue
from transactions.models import Transaction


@dataclass(frozen=True)
class ResultadoRevisaoManual:
    """Resultado de uma revisão manual aplicada em uma pendência."""

    review_queue_id: int
    transaction_id: int
    ja_resolvida: bool
    merchant_map_criado: bool
    merchant_map_existente: bool


def revisar_transacao_manualmente(
    review_queue_id: int,
    categoria_final_id: int,
    *,
    criar_merchant_map: bool = False,
    nota_resolucao: str = "",
) -> ResultadoRevisaoManual:
    """
    Aplica revisão manual em Transaction e resolve a ReviewQueue correspondente.

    Regras MVP:
    - classificação manual sempre define `classification_source=manual`.
    - confiança manual usa valor alto e fixo para auditabilidade.
    - revisão pendente passa para `resolved`.
    """

    with transaction.atomic():
        revisao = (
            ReviewQueue.objects.select_for_update()
            .select_related("transaction")
            .get(pk=review_queue_id)
        )
        transacao = (
            Transaction.objects.select_for_update()
            .select_related("category")
            .get(pk=revisao.transaction_id)
        )

        if revisao.status == ReviewQueue.Status.RESOLVED and transacao.category_id == categoria_final_id:
            return ResultadoRevisaoManual(
                review_queue_id=revisao.id,
                transaction_id=transacao.id,
                ja_resolvida=True,
                merchant_map_criado=False,
                merchant_map_existente=False,
            )

        _aplicar_classificacao_manual(transacao, categoria_final_id)
        _resolver_review_queue(revisao, nota_resolucao)

        merchant_map_criado = False
        merchant_map_existente = False
        if criar_merchant_map:
            merchant_map_criado, merchant_map_existente = _criar_merchant_map_se_aplicavel(
                merchant_norm=transacao.merchant_norm,
                categoria_final_id=categoria_final_id,
            )

        return ResultadoRevisaoManual(
            review_queue_id=revisao.id,
            transaction_id=transacao.id,
            ja_resolvida=False,
            merchant_map_criado=merchant_map_criado,
            merchant_map_existente=merchant_map_existente,
        )


def _aplicar_classificacao_manual(transacao: Transaction, categoria_final_id: int) -> None:
    transacao.category_id = categoria_final_id
    transacao.classification_source = Transaction.ClassificationSource.MANUAL
    transacao.classification_confidence = Decimal("1.00")
    transacao.save(update_fields=["category", "classification_source", "classification_confidence", "updated_at"])


def _resolver_review_queue(revisao: ReviewQueue, nota_resolucao: str) -> None:
    revisao.status = ReviewQueue.Status.RESOLVED
    revisao.resolved_at = timezone.now()
    revisao.resolution_note = nota_resolucao or "Revisão manual aplicada via Django Admin."
    revisao.save(update_fields=["status", "resolved_at", "resolution_note"])


def _criar_merchant_map_se_aplicavel(merchant_norm: str, categoria_final_id: int) -> tuple[bool, bool]:
    merchant_limpo = (merchant_norm or "").strip()
    if not merchant_limpo:
        return False, False

    merchant_map, criado = MerchantMap.objects.get_or_create(
        merchant_norm=merchant_limpo,
        category_id=categoria_final_id,
        defaults={
            "source": MerchantMap.Source.MANUAL_REVIEW,
            "confidence": Decimal("1.000"),
        },
    )
    if criado:
        return True, False
    if merchant_map.source != MerchantMap.Source.MANUAL_REVIEW:
        merchant_map.source = MerchantMap.Source.MANUAL_REVIEW
        merchant_map.save(update_fields=["source", "updated_at"])
    return False, True
