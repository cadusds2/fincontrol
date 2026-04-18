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
from classification.services.similarity import buscar_similaridade_fuzzy, score_para_confianca
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

        categoria_par_pix_credito = _classificar_par_pix_credito(transacao)
        if categoria_par_pix_credito is not None:
            _resolver_revisao_pendente(transacao, "Classificacao automatica por par Pix no Credito.")
            return ResultadoClassificacao(
                origem=Transaction.ClassificationSource.RULE,
                categoria_id=categoria_par_pix_credito.id,
                criou_revisao=False,
            )

        resultado_regra_prioritaria = _classificar_por_regra_tecnica_prioritaria(transacao)
        if resultado_regra_prioritaria is not None:
            _aplicar_classificacao(
                transacao=transacao,
                categoria_id=resultado_regra_prioritaria.categoria.id,
                origem=Transaction.ClassificationSource.RULE,
                confianca=resultado_regra_prioritaria.confianca,
            )
            _resolver_revisao_pendente(transacao, "Classificacao automatica por regra tecnica prioritaria.")
            return ResultadoClassificacao(
                origem=Transaction.ClassificationSource.RULE,
                categoria_id=resultado_regra_prioritaria.categoria.id,
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

        resultado_similaridade = buscar_similaridade_fuzzy(transacao)
        if resultado_similaridade is not None:
            if resultado_similaridade.action == "auto" and resultado_similaridade.category is not None:
                _aplicar_classificacao(
                    transacao=transacao,
                    categoria_id=resultado_similaridade.category.id,
                    origem=Transaction.ClassificationSource.SIMILARITY,
                    confianca=score_para_confianca(resultado_similaridade.score),
                )
                if resultado_similaridade.merchant_map is not None:
                    MerchantMap.objects.filter(pk=resultado_similaridade.merchant_map.pk).update(
                        usage_count=F("usage_count") + 1,
                        last_used_at=timezone.now(),
                    )
                _resolver_revisao_pendente(transacao, "Classificacao automatica por similaridade fuzzy.")
                return ResultadoClassificacao(
                    origem=Transaction.ClassificationSource.SIMILARITY,
                    categoria_id=resultado_similaridade.category.id,
                    criou_revisao=False,
                )

            _marcar_nao_classificada(transacao)
            reason = (
                ReviewQueue.Reason.CONFLICT
                if resultado_similaridade.action == "conflict"
                else ReviewQueue.Reason.LOW_CONFIDENCE
            )
            criado = _garantir_review_queue_pendente(
                transacao,
                reason=reason,
                suggested_category=resultado_similaridade.category,
            )
            return ResultadoClassificacao(
                origem=Transaction.ClassificationSource.UNCLASSIFIED,
                categoria_id=None,
                criou_revisao=criado,
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


def _classificar_por_regra_tecnica_prioritaria(transacao: Transaction):
    texto_base = " ".join(
        [
            (transacao.description_norm or "").casefold(),
            (transacao.merchant_norm or "").casefold(),
        ]
    )
    if not (
        ("pagamento" in texto_base and "fatura" in texto_base)
        or ("aplicacao" in texto_base and "rdb" in texto_base)
    ):
        return None
    return aplicar_regras_deterministicas(transacao)


def _classificar_par_pix_credito(transacao: Transaction) -> Category | None:
    if not transacao.external_id or not _eh_lancamento_pix_credito(transacao):
        return None

    contraparte = (
        Transaction.objects.select_for_update()
        .filter(
            account_id=transacao.account_id,
            external_id=transacao.external_id,
            transaction_date=transacao.transaction_date,
            amount=transacao.amount,
        )
        .exclude(pk=transacao.pk)
        .first()
    )
    if contraparte is None or contraparte.direction == transacao.direction:
        return None
    if not _forma_par_pix_credito(transacao, contraparte):
        return None

    categoria_transferencia_interna = Category.objects.filter(
        slug="transferencia-interna",
        kind=Category.Kind.TECNICA,
        is_reportable=False,
        is_active=True,
    ).first()
    if categoria_transferencia_interna is None:
        return None

    for item in (transacao, contraparte):
        _aplicar_classificacao(
            transacao=item,
            categoria_id=categoria_transferencia_interna.id,
            origem=Transaction.ClassificationSource.RULE,
            confianca=Decimal("0.96"),
        )
        _resolver_revisao_pendente(item, "Classificacao automatica por par Pix no Credito.")

    return categoria_transferencia_interna


def _eh_lancamento_pix_credito(transacao: Transaction) -> bool:
    texto = (transacao.description_norm or "").casefold()
    return (
        "valor adicionado" in texto
        and "pix no credito" in texto
    ) or (
        "transferencia enviada" in texto
        and "pix" in texto
    )


def _forma_par_pix_credito(transacao: Transaction, contraparte: Transaction) -> bool:
    descricoes = {
        "valor_adicionado": False,
        "pix_enviado": False,
    }
    for item in (transacao, contraparte):
        texto = (item.description_norm or "").casefold()
        if "valor adicionado" in texto and "pix no credito" in texto:
            descricoes["valor_adicionado"] = True
        if "transferencia enviada" in texto and "pix" in texto:
            descricoes["pix_enviado"] = True
    return all(descricoes.values())


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


def _garantir_review_queue_pendente(
    transacao: Transaction,
    *,
    reason: str = ReviewQueue.Reason.NO_MATCH,
    suggested_category: Category | None = None,
) -> bool:
    review, criado = ReviewQueue.objects.get_or_create(
        transaction=transacao,
        defaults={
            "reason": reason,
            "status": ReviewQueue.Status.PENDING,
            "suggested_category": suggested_category,
        },
    )
    if not criado and (
        review.status != ReviewQueue.Status.PENDING
        or review.reason != reason
        or review.suggested_category_id != (suggested_category.id if suggested_category else None)
    ):
        review.status = ReviewQueue.Status.PENDING
        review.reason = reason
        review.suggested_category = suggested_category
        review.resolved_at = None
        review.resolution_note = ""
        review.save(update_fields=["status", "reason", "suggested_category", "resolved_at", "resolution_note"])
    return criado


def _resolver_revisao_pendente(transacao: Transaction, observacao: str) -> None:
    review = ReviewQueue.objects.filter(transaction=transacao).first()
    if not review or review.status != ReviewQueue.Status.PENDING:
        return
    review.status = ReviewQueue.Status.RESOLVED
    review.resolved_at = timezone.now()
    review.resolution_note = observacao
    review.save(update_fields=["status", "resolved_at", "resolution_note"])
