from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models


class Budget(models.Model):
    """Orçamento mensal por categoria de consumo."""

    period_month = models.CharField(
        max_length=7,
        validators=[RegexValidator(regex=r"^\d{4}-(0[1-9]|1[0-2])$", message="Use o formato YYYY-MM.")],
    )
    category = models.ForeignKey("classification.Category", on_delete=models.PROTECT, related_name="budgets")
    planned_amount = models.DecimalField(max_digits=14, decimal_places=2)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-period_month", "category__name"]
        verbose_name = "Orçamento"
        verbose_name_plural = "Orçamentos"
        constraints = [
            models.UniqueConstraint(fields=["period_month", "category"], name="budget_period_month_category_unico")
        ]

    def __str__(self) -> str:
        return f"{self.period_month} - {self.category.name}"

    def clean(self) -> None:
        super().clean()
        if self.category_id and self.category.kind != self.category.Kind.CONSUMO:
            raise ValidationError({"category": "Budget só pode apontar para categoria com kind=consumo."})
