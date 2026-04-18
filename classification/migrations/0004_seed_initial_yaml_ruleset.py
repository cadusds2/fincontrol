import hashlib

from django.db import migrations
from django.utils import timezone


INITIAL_RULESET_YAML = """version: 1
rules:
  - id: pagamento_fatura
    priority: 100
    category_slug: pagamento-de-fatura
    confidence: "0.95"
    when:
      any:
        - field: description_norm
          contains_all:
            - pagamento
            - fatura
        - field: merchant_norm
          contains_all:
            - pagamento
            - fatura

  - id: transferencia_interna_textual
    priority: 95
    category_slug: transferencia-interna
    confidence: "0.95"
    when:
      any:
        - field: description_norm
          contains_all:
            - transferencia
            - interna
        - field: merchant_norm
          contains_all:
            - transferencia
            - interna
        - field: description_norm
          contains_all:
            - transferencia
            - entre
            - contas
        - field: merchant_norm
          contains_all:
            - transferencia
            - entre
            - contas
        - field: description_norm
          contains_all:
            - pix
            - propria
        - field: merchant_norm
          contains_all:
            - pix
            - propria

  - id: movimentacao_investimentos
    priority: 90
    category_slug: movimentacao-de-investimentos
    confidence: "0.95"
    when:
      any:
        - field: description_norm
          contains_all:
            - movimentacao
            - investimentos
        - field: merchant_norm
          contains_all:
            - movimentacao
            - investimentos
        - field: description_norm
          contains_all:
            - resgate
            - investimento
        - field: merchant_norm
          contains_all:
            - resgate
            - investimento
        - field: description_norm
          contains_all:
            - aplicacao
            - investimento
        - field: merchant_norm
          contains_all:
            - aplicacao
            - investimento
        - field: description_norm
          contains_all:
            - aplicacao
            - rdb
        - field: merchant_norm
          contains_all:
            - aplicacao
            - rdb
"""


def seed_initial_ruleset(apps, schema_editor):
    ClassificationRuleSet = apps.get_model("classification", "ClassificationRuleSet")
    if ClassificationRuleSet.objects.filter(status="active").exists():
        return
    checksum = hashlib.sha256(INITIAL_RULESET_YAML.encode("utf-8")).hexdigest()
    ClassificationRuleSet.objects.create(
        name="Regras MVP iniciais",
        version=1,
        status="active",
        yaml_content=INITIAL_RULESET_YAML,
        checksum=checksum,
        validation_errors="",
        activated_at=timezone.now(),
    )


def remove_initial_ruleset(apps, schema_editor):
    ClassificationRuleSet = apps.get_model("classification", "ClassificationRuleSet")
    ClassificationRuleSet.objects.filter(
        name="Regras MVP iniciais",
        version=1,
        checksum=hashlib.sha256(INITIAL_RULESET_YAML.encode("utf-8")).hexdigest(),
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("classification", "0003_classificationruleset"),
    ]

    operations = [
        migrations.RunPython(seed_initial_ruleset, remove_initial_ruleset),
    ]
