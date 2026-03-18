from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.apps import apps


class Transaction(models.Model):
    """Lançamento canônico importado para classificação e relatório."""

    class Direction(models.TextChoices):
        DEBITO = "debit", "Débito"
        CREDITO = "credit", "Crédito"

    class ClassificationSource(models.TextChoices):
        MERCHANT_MAP = "merchant_map", "Merchant map"
        REGRA = "rule", "Regra"
        SIMILARIDADE = "similarity", "Similaridade"
        MANUAL = "manual", "Manual"
        NAO_CLASSIFICADA = "unclassified", "Não classificada"

    import_batch = models.ForeignKey("imports.ImportBatch", on_delete=models.PROTECT, related_name="transactions")
    account = models.ForeignKey("accounts.Account", on_delete=models.PROTECT, related_name="transactions")
    transaction_date = models.DateField()
    description_raw = models.TextField()
    description_norm = models.TextField()
    merchant_norm = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default="BRL")
    direction = models.CharField(max_length=10, choices=Direction.choices)
    raw_hash = models.CharField(max_length=64)
    classification_source = models.CharField(
        max_length=20,
        choices=ClassificationSource.choices,
        default=ClassificationSource.NAO_CLASSIFICADA,
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
    is_installment = models.BooleanField(null=True, blank=True)
    installment_current = models.PositiveSmallIntegerField(null=True, blank=True)
    installment_total = models.PositiveSmallIntegerField(null=True, blank=True)
    installment_key = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-transaction_date", "-id"]
        verbose_name = "Transação"
        verbose_name_plural = "Transações"
        constraints = [
            models.UniqueConstraint(fields=["account", "raw_hash"], name="transaction_account_raw_hash_unico")
        ]

    def clean(self) -> None:
        super().clean()
        if self._state.adding and self.classification_source != self.ClassificationSource.NAO_CLASSIFICADA:
            raise ValidationError({"classification_source": "Novas transações devem iniciar como unclassified."})

        if not self.import_batch_id or not self.account_id:
            return

        import_batch_model = apps.get_model("imports", "ImportBatch")
        import_batch_account_id = import_batch_model.objects.filter(pk=self.import_batch_id).values_list(
            "account_id", flat=True
        ).first()
        if import_batch_account_id is None:
            raise ValidationError({"import_batch": "ImportBatch informado não existe."})

        if import_batch_account_id != self.account_id:
            raise ValidationError({"import_batch": "import_batch.account deve ser igual a transaction.account."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.transaction_date} - {self.amount} {self.currency}"
