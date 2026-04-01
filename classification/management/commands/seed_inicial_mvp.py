"""Comando para popular dados iniciais do MVP de forma idempotente."""

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from accounts.models import Account
from classification.models import Category


class Command(BaseCommand):
    help = "Popula categorias e contas iniciais do MVP de forma idempotente."

    categorias_consumo = (
        "Moradia",
        "Alimentação",
        "Transporte",
        "Saúde",
        "Lazer",
        "Assinaturas",
        "Educação",
        "Compras",
        "Contas/Serviços",
        "Investimentos",
        "Outros",
    )

    categorias_tecnicas = (
        "Pagamento de Fatura",
        "Transferência Interna",
        "Movimentação de Investimentos",
    )

    contas_iniciais = (
        {
            "bank_name": "Nubank",
            "account_type": Account.AccountType.CHECKING,
            "display_name": "Nubank Conta",
        },
        {
            "bank_name": "Nubank",
            "account_type": Account.AccountType.CREDIT_CARD,
            "display_name": "Nubank Cartão 1",
        },
        {
            "bank_name": "Nubank",
            "account_type": Account.AccountType.CREDIT_CARD,
            "display_name": "Nubank Cartão 2",
        },
        {
            "bank_name": "Itaú",
            "account_type": Account.AccountType.CHECKING,
            "display_name": "Itaú Conta",
        },
        {
            "bank_name": "Itaú",
            "account_type": Account.AccountType.CREDIT_CARD,
            "display_name": "Itaú Cartão 1",
        },
        {
            "bank_name": "Itaú",
            "account_type": Account.AccountType.CREDIT_CARD,
            "display_name": "Itaú Cartão 2",
        },
    )

    def handle(self, *args, **options):
        categorias_criadas, categorias_atualizadas = self._popular_categorias()
        contas_criadas, contas_atualizadas = self._popular_contas()

        self.stdout.write(
            self.style.SUCCESS(
                "Seed inicial concluído. "
                f"Categorias criadas: {categorias_criadas}; "
                f"categorias atualizadas: {categorias_atualizadas}; "
                f"contas criadas: {contas_criadas}; "
                f"contas atualizadas: {contas_atualizadas}."
            )
        )

    def _popular_categorias(self):
        criadas = 0
        atualizadas = 0

        for nome in self.categorias_consumo:
            _, criado = Category.objects.update_or_create(
                slug=slugify(nome),
                defaults={
                    "name": nome,
                    "kind": Category.Kind.CONSUMO,
                    "is_reportable": True,
                    "is_active": True,
                },
            )
            if criado:
                criadas += 1
            else:
                atualizadas += 1

        for nome in self.categorias_tecnicas:
            _, criado = Category.objects.update_or_create(
                slug=slugify(nome),
                defaults={
                    "name": nome,
                    "kind": Category.Kind.TECNICA,
                    "is_reportable": False,
                    "is_active": True,
                },
            )
            if criado:
                criadas += 1
            else:
                atualizadas += 1

        return criadas, atualizadas

    def _popular_contas(self):
        criadas = 0
        atualizadas = 0

        for conta in self.contas_iniciais:
            _, criado = Account.objects.update_or_create(
                bank_name=conta["bank_name"],
                account_type=conta["account_type"],
                display_name=conta["display_name"],
                defaults={"is_active": True},
            )
            if criado:
                criadas += 1
            else:
                atualizadas += 1

        return criadas, atualizadas
