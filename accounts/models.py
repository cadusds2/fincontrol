from django.db import models


class Account(models.Model):
    """Conta corrente ou cartão de crédito de origem das transações."""

    class TipoConta(models.TextChoices):
        CONTA_CORRENTE = "checking", "Conta corrente"
        CARTAO_CREDITO = "credit_card", "Cartão de crédito"

    bank_name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=20, choices=TipoConta.choices)
    display_name = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)
    external_ref = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["bank_name", "display_name"]
        verbose_name = "Conta"
        verbose_name_plural = "Contas"

    def __str__(self) -> str:
        return f"{self.display_name} ({self.bank_name})"
