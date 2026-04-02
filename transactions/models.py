"""Modelos de domínio do app transactions."""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Transaction(models.Model):
    """Lançamento financeiro canônico para classificação e relatório."""

    class Direction(models.TextChoices):
        DEBIT = "debit", "Débito"
        CREDIT = "credit", "Crédito"

    class ClassificationSource(models.TextChoices):
        MERCHANT_MAP = "merchant_map", "MerchantMap"
        RULE = "rule", "Regra"
        SIMILARITY = "similarity", "Similaridade"
        MANUAL = "manual", "Manual"
        UNCLASSIFIED = "unclassified", "Não classificado"

    import_batch = models.ForeignKey(
        "imports.ImportBatch",
        on_delete=models.PROTECT,
        related_name="transactions",
    )
    account = models.ForeignKey(
        "accounts.Account",
        on_delete=models.PROTECT,
        related_name="transactions",
    )
    transaction_date = models.DateField()
    description_raw = models.TextField()
    description_norm = models.TextField()
    merchant_raw = models.CharField(max_length=255, blank=True, default="")
    merchant_norm = models.CharField(max_length=255, db_index=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default="BRL")
    direction = models.CharField(max_length=10, choices=Direction.choices)
    raw_hash = models.CharField(max_length=64)
    classification_source = models.CharField(
        max_length=20,
        choices=ClassificationSource.choices,
        default=ClassificationSource.UNCLASSIFIED,
    )

    posted_date = models.DateField(null=True, blank=True)
    category = models.ForeignKey(
        "classification.Category",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
    )
    classification_confidence = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
    )
    is_installment = models.BooleanField(default=False)
    installment_current = models.PositiveSmallIntegerField(null=True, blank=True)
    installment_total = models.PositiveSmallIntegerField(null=True, blank=True)
    installment_key = models.CharField(max_length=120, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-transaction_date", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["account", "raw_hash"],
                name="uniq_transaction_account_raw_hash",
            )
        ]

    def __str__(self) -> str:
        return f"{self.transaction_date} - {self.amount} - {self.description_raw[:40]}"
