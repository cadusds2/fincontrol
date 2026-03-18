from django.core.exceptions import ValidationError
from django.db import models


class ImportBatch(models.Model):
    """Execução de importação manual de CSV."""

    class TipoArquivo(models.TextChoices):
        EXTRATO_CONTA_NUBANK = "extrato_conta_nubank", "Extrato conta Nubank"
        FATURA_CARTAO_NUBANK = "fatura_cartao_nubank", "Fatura cartão Nubank"
        EXTRATO_CONTA_ITAU = "extrato_conta_itau", "Extrato conta Itaú"
        FATURA_CARTAO_ITAU = "fatura_cartao_itau", "Fatura cartão Itaú"

    class Status(models.TextChoices):
        RECEBIDO = "received", "Recebido"
        PROCESSADO = "processed", "Processado"
        PARCIAL = "partial", "Parcial"
        FALHOU = "failed", "Falhou"

    account = models.ForeignKey("accounts.Account", on_delete=models.PROTECT, related_name="import_batches")
    file_type = models.CharField(max_length=40, choices=TipoArquivo.choices)
    source_filename = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=Status.choices)
    total_rows = models.PositiveIntegerField(default=0)
    imported_rows = models.PositiveIntegerField(default=0)
    duplicated_rows = models.PositiveIntegerField(default=0)
    imported_at = models.DateTimeField()
    error_log = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-imported_at", "-id"]
        verbose_name = "Lote de importação"
        verbose_name_plural = "Lotes de importação"

    def __str__(self) -> str:
        return f"{self.source_filename} - {self.get_status_display()}"

    def clean(self) -> None:
        super().clean()
        if not self.pk:
            return

        previous_account_id = (
            ImportBatch.objects.filter(pk=self.pk).values_list("account_id", flat=True).first()
        )
        if previous_account_id is None:
            return

        if previous_account_id != self.account_id and self.transactions.exists():
            raise ValidationError(
                {"account": "Não é permitido trocar account de um lote que já possui transações importadas."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
