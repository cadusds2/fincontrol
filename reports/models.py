"""Modelos de domínio do app reports."""

from django.core.exceptions import ValidationError
from django.db import models


class Budget(models.Model):
    """Orçamento mensal por categoria de consumo."""

    period_month = models.CharField(max_length=7, help_text="Formato YYYY-MM")
    category = models.ForeignKey(
        "classification.Category",
        on_delete=models.PROTECT,
        related_name="budgets",
    )
    planned_amount = models.DecimalField(max_digits=14, decimal_places=2)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-period_month", "category__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["period_month", "category"],
                name="uniq_budget_period_category",
            )
        ]

    def clean(self) -> None:
        super().clean()
        if self.category_id and self.category.kind != "consumo":
            raise ValidationError("Budget deve apontar para categoria de consumo.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.period_month} - {self.category.name}"
