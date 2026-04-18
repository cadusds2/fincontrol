"""Motor de regras YAML para classificacao deterministica do MVP."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import re
from typing import Any

import yaml
from django.db import transaction
from django.utils import timezone

from classification.models import Category, ClassificationRuleSet
from transactions.models import Transaction


ALLOWED_FIELDS = {"description_norm", "merchant_norm", "direction", "currency"}
ALLOWED_OPERATORS = {"contains", "contains_all", "equals", "in"}
RULE_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


@dataclass(frozen=True)
class YamlRuleMatch:
    """Resultado interno de uma regra YAML aplicada."""

    categoria: Category
    confianca: Decimal
    rule_id: str


@dataclass(frozen=True)
class ValidationResult:
    """Resultado de validacao de um ruleset YAML."""

    valid: bool
    errors: tuple[str, ...]
    checksum: str
    parsed: dict[str, Any] | None = None


def calcular_checksum(yaml_content: str) -> str:
    return hashlib.sha256((yaml_content or "").encode("utf-8")).hexdigest()


def anexar_regra_yaml(
    yaml_content: str,
    regra: dict[str, Any],
    *,
    default_version: int,
) -> tuple[str | None, ValidationResult]:
    """Anexa uma regra ao YAML atual e retorna o novo conteudo validado."""

    checksum_atual = calcular_checksum(yaml_content)
    try:
        parsed = yaml.safe_load(yaml_content or "")
    except yaml.YAMLError as exc:
        return None, ValidationResult(
            valid=False,
            errors=(f"YAML atual invalido: {exc}",),
            checksum=checksum_atual,
            parsed=None,
        )

    if parsed is None:
        parsed = {"version": default_version, "rules": []}

    if not isinstance(parsed, dict):
        return None, ValidationResult(
            valid=False,
            errors=("O YAML atual deve ter um objeto raiz com 'version' e 'rules'.",),
            checksum=checksum_atual,
            parsed=None,
        )

    parsed.setdefault("version", default_version)
    rules = parsed.setdefault("rules", [])
    if not isinstance(rules, list):
        return None, ValidationResult(
            valid=False,
            errors=("'rules' do YAML atual deve ser uma lista.",),
            checksum=checksum_atual,
            parsed=None,
        )

    rule_id = regra.get("id")
    ids_existentes = {
        item.get("id")
        for item in rules
        if isinstance(item, dict)
    }
    if rule_id in ids_existentes:
        return None, ValidationResult(
            valid=False,
            errors=(f"Ja existe uma regra com id '{rule_id}'.",),
            checksum=checksum_atual,
            parsed=None,
        )

    rules.append(regra)
    novo_yaml = yaml.safe_dump(
        parsed,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    )
    resultado = validar_yaml_ruleset(novo_yaml)
    if not resultado.valid:
        return None, resultado
    return novo_yaml, resultado


def validar_yaml_ruleset(yaml_content: str) -> ValidationResult:
    checksum = calcular_checksum(yaml_content)
    errors: list[str] = []

    try:
        parsed = yaml.safe_load(yaml_content or "")
    except yaml.YAMLError as exc:
        return ValidationResult(
            valid=False,
            errors=(f"YAML invalido: {exc}",),
            checksum=checksum,
            parsed=None,
        )

    if not isinstance(parsed, dict):
        return ValidationResult(
            valid=False,
            errors=("O YAML deve ter um objeto raiz com 'version' e 'rules'.",),
            checksum=checksum,
            parsed=None,
        )

    version = parsed.get("version")
    if not isinstance(version, int) or version <= 0:
        errors.append("'version' deve ser um inteiro positivo.")

    rules = parsed.get("rules")
    if not isinstance(rules, list) or not rules:
        errors.append("'rules' deve ser uma lista nao vazia.")
        rules = []

    seen_ids: set[str] = set()
    for index, rule in enumerate(rules, start=1):
        prefix = f"Regra #{index}"
        if not isinstance(rule, dict):
            errors.append(f"{prefix}: cada regra deve ser um objeto.")
            continue

        rule_id = rule.get("id")
        if not isinstance(rule_id, str) or not RULE_ID_PATTERN.match(rule_id):
            errors.append(f"{prefix}: 'id' deve ser snake_case e comecar com letra.")
        elif rule_id in seen_ids:
            errors.append(f"{prefix}: id duplicado '{rule_id}'.")
        else:
            seen_ids.add(rule_id)

        priority = rule.get("priority")
        if not isinstance(priority, int):
            errors.append(f"{prefix}: 'priority' deve ser inteiro.")

        category_slug = rule.get("category_slug")
        if not isinstance(category_slug, str) or not category_slug.strip():
            errors.append(f"{prefix}: 'category_slug' e obrigatorio.")
        elif not Category.objects.filter(slug=category_slug, is_active=True).exists():
            errors.append(f"{prefix}: categoria ativa '{category_slug}' nao encontrada.")

        confidence = _parse_confidence(rule.get("confidence"))
        if confidence is None:
            errors.append(f"{prefix}: 'confidence' deve ser decimal entre 0 e 1.")

        when = rule.get("when")
        if not isinstance(when, dict):
            errors.append(f"{prefix}: 'when' e obrigatorio e deve ser um objeto.")
        else:
            errors.extend(_validate_condition_group(when, prefix))

    return ValidationResult(
        valid=not errors,
        errors=tuple(errors),
        checksum=checksum,
        parsed=parsed if not errors else None,
    )


def ativar_ruleset(ruleset: ClassificationRuleSet) -> ValidationResult:
    resultado = validar_yaml_ruleset(ruleset.yaml_content)
    ruleset.validation_errors = "\n".join(resultado.errors)
    ruleset.checksum = resultado.checksum
    if not resultado.valid:
        ruleset.save(update_fields=["validation_errors", "checksum", "updated_at"])
        return resultado

    with transaction.atomic():
        ClassificationRuleSet.objects.select_for_update().filter(
            status=ClassificationRuleSet.Status.ACTIVE
        ).exclude(pk=ruleset.pk).update(status=ClassificationRuleSet.Status.ARCHIVED)

        ruleset.status = ClassificationRuleSet.Status.ACTIVE
        ruleset.activated_at = timezone.now()
        ruleset.validation_errors = ""
        ruleset.checksum = resultado.checksum
        ruleset.save(
            update_fields=[
                "status",
                "activated_at",
                "validation_errors",
                "checksum",
                "updated_at",
            ]
        )
    return resultado


def aplicar_regras_yaml(transacao: Transaction) -> YamlRuleMatch | None:
    ruleset = ClassificationRuleSet.objects.filter(
        status=ClassificationRuleSet.Status.ACTIVE
    ).first()
    if ruleset is None:
        return None

    resultado = validar_yaml_ruleset(ruleset.yaml_content)
    if not resultado.valid or resultado.parsed is None:
        return None

    ordered_rules = sorted(
        resultado.parsed["rules"],
        key=lambda item: (-item["priority"], item["id"]),
    )
    for rule in ordered_rules:
        if not _evaluate_condition_group(rule["when"], transacao):
            continue

        categoria = Category.objects.filter(
            slug=rule["category_slug"],
            is_active=True,
        ).first()
        if categoria is None:
            continue

        confidence = _parse_confidence(rule["confidence"])
        if confidence is None:
            continue
        return YamlRuleMatch(
            categoria=categoria,
            confianca=confidence,
            rule_id=rule["id"],
        )

    return None


def _validate_condition_group(group: dict[str, Any], prefix: str) -> list[str]:
    errors: list[str] = []
    keys = set(group)
    if keys != {"all"} and keys != {"any"}:
        return [f"{prefix}: 'when' deve conter exatamente 'all' ou 'any'."]

    operator = "all" if "all" in group else "any"
    conditions = group[operator]
    if not isinstance(conditions, list) or not conditions:
        return [f"{prefix}: '{operator}' deve ser uma lista nao vazia."]

    for condition_index, condition in enumerate(conditions, start=1):
        condition_prefix = f"{prefix}, condicao #{condition_index}"
        if not isinstance(condition, dict):
            errors.append(f"{condition_prefix}: condicao deve ser um objeto.")
            continue

        if "all" in condition or "any" in condition:
            errors.extend(_validate_condition_group(condition, condition_prefix))
            continue

        field = condition.get("field")
        if field not in ALLOWED_FIELDS:
            errors.append(
                f"{condition_prefix}: field '{field}' invalido. Permitidos: {', '.join(sorted(ALLOWED_FIELDS))}."
            )

        operators = [key for key in condition if key != "field"]
        if len(operators) != 1:
            errors.append(f"{condition_prefix}: informe exatamente um operador.")
            continue

        operator_name = operators[0]
        if operator_name not in ALLOWED_OPERATORS:
            errors.append(
                f"{condition_prefix}: operador '{operator_name}' invalido. Permitidos: {', '.join(sorted(ALLOWED_OPERATORS))}."
            )
            continue

        value = condition[operator_name]
        if operator_name in {"contains", "equals"} and not isinstance(value, str):
            errors.append(f"{condition_prefix}: '{operator_name}' deve receber texto.")
        if operator_name in {"contains_all", "in"} and (
            not isinstance(value, list) or not value or not all(isinstance(item, str) for item in value)
        ):
            errors.append(f"{condition_prefix}: '{operator_name}' deve receber lista de textos.")

    return errors


def _evaluate_condition_group(group: dict[str, Any], transacao: Transaction) -> bool:
    if "all" in group:
        return all(_evaluate_condition(condition, transacao) for condition in group["all"])
    if "any" in group:
        return any(_evaluate_condition(condition, transacao) for condition in group["any"])
    return False


def _evaluate_condition(condition: dict[str, Any], transacao: Transaction) -> bool:
    if "all" in condition or "any" in condition:
        return _evaluate_condition_group(condition, transacao)

    field = condition["field"]
    current_value = _normalize_value(getattr(transacao, field, ""))
    if "contains" in condition:
        return _normalize_value(condition["contains"]) in current_value
    if "contains_all" in condition:
        return all(_normalize_value(term) in current_value for term in condition["contains_all"])
    if "equals" in condition:
        return current_value == _normalize_value(condition["equals"])
    if "in" in condition:
        return current_value in {_normalize_value(item) for item in condition["in"]}
    return False


def _parse_confidence(value: Any) -> Decimal | None:
    try:
        confidence = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    if Decimal("0") <= confidence <= Decimal("1"):
        return confidence
    return None


def _normalize_value(value: Any) -> str:
    return str(value or "").casefold().strip()
