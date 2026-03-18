from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from classification.models import Category
from reports.models import Budget


class BudgetModelTests(TestCase):
    def setUp(self) -> None:
        self.categoria_consumo = Category.objects.create(
            name="Alimentação",
            slug="alimentacao",
            kind=Category.Kind.CONSUMO,
            is_reportable=True,
        )
        self.categoria_tecnica = Category.objects.create(
            name="Pagamento de Fatura",
            slug="pagamento-fatura",
            kind=Category.Kind.TECNICA,
            is_reportable=False,
        )

    def test_clean_rejeita_categoria_tecnica(self) -> None:
        budget = Budget(
            period_month="2026-03",
            category=self.categoria_tecnica,
            planned_amount=Decimal("100.00"),
        )

        with self.assertRaises(ValidationError):
            budget.clean()

    def test_create_rejeita_categoria_tecnica_no_save(self) -> None:
        with self.assertRaises(ValidationError):
            Budget.objects.create(
                period_month="2026-03",
                category=self.categoria_tecnica,
                planned_amount=Decimal("100.00"),
            )

    def test_create_aceita_categoria_consumo(self) -> None:
        budget = Budget.objects.create(
            period_month="2026-03",
            category=self.categoria_consumo,
            planned_amount=Decimal("350.00"),
        )

        self.assertEqual(budget.category_id, self.categoria_consumo.id)
