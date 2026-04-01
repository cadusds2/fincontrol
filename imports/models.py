"""Modelos de domínio do app imports."""

from django.db import models
from django.utils import timezone


class ImportBatch(models.Model):
    """Rastreia uma execução de importação manual de CSV."""

    class FileType(models.TextChoices):
        EXTRATO_CONTA_NUBANK = "extrato_conta_nubank", "Extrato conta Nubank"
        FATURA_CARTAO_NUBANK = "fatura_cartao_nubank", "Fatura cartão Nubank"
        EXTRATO_CONTA_ITAU = "extrato_conta_itau", "Extrato conta Itaú"
        FATURA_CARTAO_ITAU = "fatura_cartao_itau", "Fatura cartão Itaú"

    class Status(models.TextChoices):
        RECEIVED = "received", "Recebido"
        PROCESSED = "processed", "Processado"
        PARTIAL = "partial", "Parcial"
        FAILED = "failed", "Falhou"

    account = models.ForeignKey(
        "accounts.Account",
        on_delete=models.PROTECT,
        related_name="import_batches",
    )
    file = models.FileField(upload_to="imports/csv/", blank=True)
    file_type = models.CharField(max_length=40, choices=FileType.choices)
    reference_month = models.DateField(
        null=True,
        blank=True,
        help_text="Use o primeiro dia do mês de referência (ex.: 2026-04-01).",
    )
    source_filename = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.RECEIVED,
    )
    rows_total = models.PositiveIntegerField(default=0)
    rows_imported = models.PositiveIntegerField(default=0)
    rows_skipped = models.PositiveIntegerField(default=0)
    total_rows = models.PositiveIntegerField(default=0)
    imported_rows = models.PositiveIntegerField(default=0)
    duplicated_rows = models.PositiveIntegerField(default=0)
    imported_at = models.DateTimeField(default=timezone.now)
    error_log = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-imported_at", "-id"]

    def __str__(self) -> str:
        return f"Lote {self.id} - {self.account.display_name} - {self.file_type}"

    def save(self, *args, **kwargs):
        if self.file and not self.source_filename:
            self.source_filename = self.file.name
        return super().save(*args, **kwargs)
