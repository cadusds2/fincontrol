from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q


class Category(models.Model):
    """Taxonomia oficial de classificação e reportabilidade."""

    class Kind(models.TextChoices):
        CONSUMO = "consumo", "Consumo"
        TECNICA = "tecnica", "Técnica"

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True)
    kind = models.CharField(max_length=20, choices=Kind.choices)
    is_reportable = models.BooleanField()
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"
        constraints = [
            models.CheckConstraint(
                check=(Q(kind="consumo", is_reportable=True) | Q(kind="tecnica", is_reportable=False)),
                name="category_kind_is_reportable_consistente",
            )
        ]

    def __str__(self) -> str:
        return self.name


class MerchantMap(models.Model):
    """Mapeamento incremental de merchant normalizado para categoria."""

    class Source(models.TextChoices):
        BASE_INICIAL = "seed", "Base inicial"
        REVISAO_MANUAL = "manual_review", "Revisão manual"

    merchant_norm = models.CharField(max_length=255)
    category = models.ForeignKey("classification.Category", on_delete=models.PROTECT, related_name="merchant_maps")
    source = models.CharField(max_length=20, choices=Source.choices)
    confidence = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
    )
    usage_count = models.PositiveIntegerField(default=0)
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["merchant_norm"]
        verbose_name = "Mapa de merchant"
        verbose_name_plural = "Mapas de merchant"

    def __str__(self) -> str:
        return f"{self.merchant_norm} -> {self.category.name}"


class ReviewQueue(models.Model):
    """Fila de revisão manual para classificação de transações."""

    class Reason(models.TextChoices):
        BAIXA_CONFIANCA = "low_confidence", "Baixa confiança"
        CONFLITO = "conflict", "Conflito"
        SEM_CORRESPONDENCIA = "no_match", "Sem correspondência"

    class Status(models.TextChoices):
        PENDENTE = "pending", "Pendente"
        RESOLVIDA = "resolved", "Resolvida"
        IGNORADA = "ignored", "Ignorada"

    transaction = models.OneToOneField(
        "transactions.Transaction",
        on_delete=models.CASCADE,
        related_name="review_queue_item",
    )
    reason = models.CharField(max_length=20, choices=Reason.choices)
    status = models.CharField(max_length=20, choices=Status.choices)
    suggested_category = models.ForeignKey(
        "classification.Category",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="review_suggestions",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["status", "-created_at"]
        verbose_name = "Fila de revisão"
        verbose_name_plural = "Fila de revisão"

    def __str__(self) -> str:
        return f"Revisão #{self.id} - {self.get_status_display()}"

    def clean(self) -> None:
        super().clean()
        if self.status in {self.Status.RESOLVIDA, self.Status.IGNORADA} and not self.resolved_at:
            raise ValidationError("resolved_at é obrigatório quando status é resolved ou ignored.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
