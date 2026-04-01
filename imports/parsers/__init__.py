"""Parsers de CSV por tipo de arquivo do MVP."""

from .itau_account import ParserItauConta
from .itau_card import ParserItauCartao
from .nubank_account import ParserNubankConta
from .nubank_card import ParserNubankCartao

MAPA_PARSERS = {
    "extrato_conta_nubank": ParserNubankConta(),
    "fatura_cartao_nubank": ParserNubankCartao(),
    "extrato_conta_itau": ParserItauConta(),
    "fatura_cartao_itau": ParserItauCartao(),
}
