"""Parsers de CSV por tipo de arquivo do MVP."""

from .itau_account import interpretar_csv_itau_conta
from .itau_card import interpretar_csv_itau_cartao
from .nubank_account import interpretar_csv_nubank_conta
from .nubank_card import interpretar_csv_nubank_cartao

MAPA_PARSERS = {
    "extrato_conta_nubank": interpretar_csv_nubank_conta,
    "fatura_cartao_nubank": interpretar_csv_nubank_cartao,
    "extrato_conta_itau": interpretar_csv_itau_conta,
    "fatura_cartao_itau": interpretar_csv_itau_cartao,
}
