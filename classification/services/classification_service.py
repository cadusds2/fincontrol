"""Serviço de classificação MVP de transações importadas."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import unicodedata

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from classification.models import Category, MerchantMap, ReviewQueue
from classification.services.rules import aplicar_regras_deterministicas
from transactions.models import Transaction


@dataclass(frozen=True)
class ResultadoClassificacao:
    """Resumo da execução de classificação para uma transação."""

    origem: str
    categoria_id: int | None
    criou_revisao: bool


def executar_classificacao_transaction(transaction_id: int) -> ResultadoClassificacao:
    """Carrega e classifica uma transação pelo pipeline oficial do MVP."""

    transacao = Transaction.objects.select_related("category").get(pk=transaction_id)
    return classificar_transacao(transacao)


def classificar_transacao(transacao: Transaction) -> ResultadoClassificacao:
    """Classifica uma transação aplicando MerchantMap e regras determinísticas."""

    with transaction.atomic():
        transacao = (
            Transaction.objects.select_for_update()
            .select_related("account")
            .get(pk=transacao.pk)
        )

        categoria_transferencia_interna = _classificar_transferencia_interna_por_alias_titular(transacao)
        if categoria_transferencia_interna is not None:
            _resolver_revisao_pendente(transacao, "Classificação automática por alias de titular.")
            return ResultadoClassificacao(
                origem=Transaction.ClassificationSource.RULE,
                categoria_id=categoria_transferencia_interna.id,
                criou_revisao=False,
            )

        resultado_merchant_map = _classificar_por_merchant_map(transacao)
        if resultado_merchant_map is not None:
            _resolver_revisao_pendente(transacao, "Classificação automática por MerchantMap.")
            return ResultadoClassificacao(
                origem=Transaction.ClassificationSource.MERCHANT_MAP,
                categoria_id=resultado_merchant_map.id,
                criou_revisao=False,
            )

        resultado_regra = aplicar_regras_deterministicas(transacao)
        if resultado_regra is not None:
            _aplicar_classificacao(
                transacao=transacao,
                categoria_id=resultado_regra.categoria.id,
                origem=Transaction.ClassificationSource.RULE,
                confianca=resultado_regra.confianca,
            )
            _resolver_revisao_pendente(transacao, "Classificação automática por regra determinística.")
            return ResultadoClassificacao(
                origem=Transaction.ClassificationSource.RULE,
                categoria_id=resultado_regra.categoria.id,
                criou_revisao=False,
            )

        _marcar_nao_classificada(transacao)
        criado = _garantir_review_queue_pendente(transacao)
        return ResultadoClassificacao(
            origem=Transaction.ClassificationSource.UNCLASSIFIED,
            categoria_id=None,
            criou_revisao=criado,
        )


def _classificar_transferencia_interna_por_alias_titular(transacao: Transaction) -> Category | None:
    merchant = _normalizar_texto_simples((transacao.merchant_norm or "").strip())
    if not merchant:
        return None

    aliases_titular = _obter_aliases_titular_da_conta(transacao)
    if not aliases_titular:
        return None

    if not _ha_match_forte_alias_titular(merchant, aliases_titular):
        return None

    categoria_transferencia_interna = Category.objects.filter(
        slug="transferencia-interna",
        kind=Category.Kind.TECNICA,
        is_reportable=False,
        is_active=True,
    ).first()
    if categoria_transferencia_interna is None:
        return None

    _aplicar_classificacao(
        transacao=transacao,
        categoria_id=categoria_transferencia_interna.id,
        origem=Transaction.ClassificationSource.RULE,
        confianca=Decimal("0.98"),
    )
    return categoria_transferencia_interna


def _obter_aliases_titular_da_conta(transacao: Transaction) -> set[str]:
    configuracao = getattr(settings, "CLASSIFICACAO_ALIASES_TITULAR", {}) or {}
    aliases_padrao = configuracao.get("padrao", [])
    aliases_por_conta = configuracao.get("por_conta", {})

    chave_conta = transacao.account.external_ref.strip() if transacao.account.external_ref else str(transacao.account_id)
    aliases_conta = aliases_por_conta.get(chave_conta, [])

    aliases_normalizados = {
        _normalizar_texto_simples(alias)
        for alias in [*aliases_padrao, *aliases_conta]
        if _normalizar_texto_simples(alias)
    }
    return aliases_normalizados


def _ha_match_forte_alias_titular(merchant: str, aliases_titular: set[str]) -> bool:
    for alias in aliases_titular:
        if merchant == alias:
            return True

        if len(alias) < 8 or len(merchant) < 8:
            continue

        if alias in merchant or merchant in alias:
            return True

    return False


def _normalizar_texto_simples(texto: str) -> str:
    texto_limpo = unicodedata.normalize("NFKD", texto or "")
    texto_limpo = "".join(char for char in texto_limpo if not unicodedata.combining(char))
    return " ".join(texto_limpo.casefold().split())


def _classificar_por_merchant_map(transacao: Transaction):
    merchant = (transacao.merchant_norm or "").strip()
    if not merchant:
        return None

    mapeamento = (
        MerchantMap.objects.select_related("category")
        .filter(merchant_norm=merchant, category__is_active=True)
        .order_by("-usage_count", "-confidence", "-updated_at", "id")
        .first()
    )
    if mapeamento is None:
        return None

    _aplicar_classificacao(
        transacao=transacao,
        categoria_id=mapeamento.category_id,
        origem=Transaction.ClassificationSource.MERCHANT_MAP,
        confianca=Decimal("0.99"),
    )

    MerchantMap.objects.filter(pk=mapeamento.pk).update(
        usage_count=F("usage_count") + 1,
        last_used_at=timezone.now(),
    )
    return mapeamento.category


def _aplicar_classificacao(
    transacao: Transaction,
    categoria_id: int,
    origem: str,
    confianca: Decimal,
) -> None:
    if (
        transacao.category_id == categoria_id
        and transacao.classification_source == origem
        and transacao.classification_confidence == confianca
    ):
        return

    transacao.category_id = categoria_id
    transacao.classification_source = origem
    transacao.classification_confidence = confianca
    transacao.save(update_fields=["category", "classification_source", "classification_confidence", "updated_at"])


def _marcar_nao_classificada(transacao: Transaction) -> None:
    if (
        transacao.category_id is None
        and transacao.classification_source == Transaction.ClassificationSource.UNCLASSIFIED
        and transacao.classification_confidence is None
    ):
        return

    transacao.category = None
    transacao.classification_source = Transaction.ClassificationSource.UNCLASSIFIED
    transacao.classification_confidence = None
    transacao.save(update_fields=["category", "classification_source", "classification_confidence", "updated_at"])


def _garantir_review_queue_pendente(transacao: Transaction) -> bool:
    review, criado = ReviewQueue.objects.get_or_create(
        transaction=transacao,
        defaults={
            "reason": ReviewQueue.Reason.NO_MATCH,
            "status": ReviewQueue.Status.PENDING,
        },
    )
    if not criado and review.status != ReviewQueue.Status.PENDING:
        review.status = ReviewQueue.Status.PENDING
        review.reason = ReviewQueue.Reason.NO_MATCH
        review.resolved_at = None
        review.resolution_note = ""
        review.save(update_fields=["status", "reason", "resolved_at", "resolution_note"])
    return criado


def _resolver_revisao_pendente(transacao: Transaction, observacao: str) -> None:
    review = ReviewQueue.objects.filter(transaction=transacao).first()
    if not review or review.status != ReviewQueue.Status.PENDING:
        return
    review.status = ReviewQueue.Status.RESOLVED
    review.resolved_at = timezone.now()
    review.resolution_note = observacao
    review.save(update_fields=["status", "resolved_at", "resolution_note"])
