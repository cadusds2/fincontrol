"""Modelos de domínio do app accounts."""

from django.db import models


class Account(models.Model):
    """Conta corrente ou cartão de crédito de origem das transações."""

    class AccountType(models.TextChoices):
        CHECKING = "checking", "Conta corrente"
        CREDIT_CARD = "credit_card", "Cartão de crédito"

    bank_name = models.CharField(max_length=120)
    account_type = models.CharField(max_length=20, choices=AccountType.choices)
    display_name = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)
    external_ref = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["bank_name", "display_name"]

    def __str__(self) -> str:
        return f"{self.display_name} ({self.bank_name})"
