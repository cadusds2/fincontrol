"""Modelos de domínio do app classification."""

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class Category(models.Model):
    """Padroniza classificação e reportabilidade."""

    class Kind(models.TextChoices):
        CONSUMO = "consumo", "Consumo"
        TECNICA = "tecnica", "Técnica"

    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True)
    kind = models.CharField(max_length=20, choices=Kind.choices)
    is_reportable = models.BooleanField()
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def clean(self) -> None:
        super().clean()
        if self.kind == self.Kind.CONSUMO and not self.is_reportable:
            raise ValidationError("Categorias de consumo devem ser reportáveis.")
        if self.kind == self.Kind.TECNICA and self.is_reportable:
            raise ValidationError("Categorias técnicas não podem ser reportáveis.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class MerchantMap(models.Model):
    """Mapeia merchant recorrente para categoria com aprendizado incremental."""

    class Source(models.TextChoices):
        SEED = "seed", "Seed"
        MANUAL_REVIEW = "manual_review", "Revisão manual"

    merchant_norm = models.CharField(max_length=255, db_index=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="merchant_maps",
    )
    source = models.CharField(max_length=20, choices=Source.choices)
    confidence = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)
    usage_count = models.PositiveIntegerField(default=0)
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["merchant_norm"]
        constraints = [
            models.UniqueConstraint(
                fields=["merchant_norm", "category"],
                name="uniq_merchant_norm_category",
            )
        ]

    def __str__(self) -> str:
        return f"{self.merchant_norm} -> {self.category.name}"


class ReviewQueue(models.Model):
    """Controla pendências de classificação manual."""

    class Reason(models.TextChoices):
        LOW_CONFIDENCE = "low_confidence", "Baixa confiança"
        CONFLICT = "conflict", "Conflito"
        NO_MATCH = "no_match", "Sem correspondência"

    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        RESOLVED = "resolved", "Resolvido"
        IGNORED = "ignored", "Ignorado"

    transaction = models.OneToOneField(
        "transactions.Transaction",
        on_delete=models.CASCADE,
        related_name="review_queue",
    )
    reason = models.CharField(max_length=20, choices=Reason.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    suggested_category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="review_suggestions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Revisão da transação {self.transaction_id} ({self.status})"


class ClassificationRuleSet(models.Model):
    """Conjunto versionado de regras YAML para classificacao deterministica."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Rascunho"
        ACTIVE = "active", "Ativo"
        ARCHIVED = "archived", "Arquivado"

    name = models.CharField(max_length=120)
    version = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    yaml_content = models.TextField("conteudo YAML", blank=True)
    checksum = models.CharField(max_length=64, blank=True)
    validation_errors = models.TextField(blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-version", "-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["status"],
                condition=Q(status="active"),
                name="uniq_active_classification_ruleset",
            )
        ]

    def __str__(self) -> str:
        return f"{self.name} v{self.version} ({self.get_status_display()})"
