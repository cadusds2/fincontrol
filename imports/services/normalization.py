"""Funções de normalização textual usadas na importação."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

PADRAO_RUIDO = re.compile(r"\b(?:compra\s+no\s+credito|debito|credito|pix|cp\s+\d+)\b")
PADRAO_ESPACOS = re.compile(r"\s+")
PADRAO_NAO_ALFANUMERICO = re.compile(r"[^\w\s/&.-]")
PADRAO_DATA_CURTA_NUBANK = re.compile(r"\b\d{1,2}(?:jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)\b")
PADRAO_HORARIO_NUBANK = re.compile(r"\b\d{1,2}h\d{2}(?:min)?\b")
PADRAO_CPF_CNPJ_MASCARADO = re.compile(
    r"\b(?:\d{3}\.?\*{3}\.?\*{3}-?\d{2}|\*{3}\.?\*{3}\.?\*{3}-?\*{2})\b"
)
PADRAO_TERMO_BANCARIO = re.compile(r"\b(?:banco|ag(?:encia)?|conta|cc)\b")
PADRAO_NUMERO_ISOLADO = re.compile(r"\b[\d.*./-]+\b")
PADRAO_TRANSFERENCIA_PIX = re.compile(r"\b(?:transferencia|pix)\b")
TERMOS_INVALIDOS_NOME_TRANSFERENCIA = {
    "pix",
    "transferencia",
    "transferencia recebida pelo pix",
    "transferencia enviada pelo pix",
    "recebida",
    "enviada",
}
PREFIXOS_MERCHANT_APOS_SEPARADOR = (
    "compra no debito via nupay",
    "ajuste de compra no debito",
    "compra no debito",
)
MERCHANTS_TECNICOS_ESTAVEIS = {
    "aplicacao rdb",
    "credito em conta",
    "pagamento de boleto efetuado",
    "pagamento de fatura",
    "valor adicionado na conta por cartao de credito",
}


@dataclass(frozen=True)
class DescricaoNormalizada:
    """Resultado canônico da normalização e extração inicial de merchant."""

    description_norm: str
    merchant_raw: str
    merchant_norm: str


def normalizar_texto(texto: str) -> str:
    """Normaliza texto para forma estável no contexto do MVP."""

    texto_limpo = unicodedata.normalize("NFKD", texto or "")
    texto_limpo = "".join(char for char in texto_limpo if not unicodedata.combining(char))
    texto_limpo = texto_limpo.casefold()
    texto_limpo = PADRAO_NAO_ALFANUMERICO.sub(" ", texto_limpo)
    texto_limpo = PADRAO_ESPACOS.sub(" ", texto_limpo).strip()
    return texto_limpo


def remover_ruido_textual(texto_normalizado: str) -> str:
    """Remove ruído textual comum mantendo legibilidade para debug."""

    sem_ruido = PADRAO_RUIDO.sub(" ", texto_normalizado)
    return PADRAO_ESPACOS.sub(" ", sem_ruido).strip()


def _limpar_trecho_nome_transferencia_ou_pix(trecho: str) -> str:
    """Remove lixo comum do trecho de nome em transferência/Pix."""

    trecho_limpo = PADRAO_CPF_CNPJ_MASCARADO.sub(" ", trecho)
    trecho_limpo = PADRAO_TERMO_BANCARIO.sub(" ", trecho_limpo)
    trecho_limpo = PADRAO_NUMERO_ISOLADO.sub(" ", trecho_limpo)
    trecho_limpo = PADRAO_ESPACOS.sub(" ", trecho_limpo).strip(" -")
    return trecho_limpo


def _limpar_ruido_operacional_nubank(trecho: str) -> str:
    """Remove data/hora operacionais do Nubank sem alterar o nome base."""

    trecho_limpo = PADRAO_DATA_CURTA_NUBANK.sub(" ", trecho)
    trecho_limpo = PADRAO_HORARIO_NUBANK.sub(" ", trecho_limpo)
    trecho_limpo = PADRAO_ESPACOS.sub(" ", trecho_limpo).strip(" -")
    return trecho_limpo


def extrair_merchant_apos_prefixo_nubank(descricao_normalizada: str) -> tuple[str, str] | None:
    """Extrai merchant em descricoes Nubank com prefixo operacional e separador."""

    partes = [parte.strip() for parte in descricao_normalizada.split("-", 1)]
    if len(partes) != 2:
        return None

    prefixo, trecho_merchant = partes
    if prefixo not in PREFIXOS_MERCHANT_APOS_SEPARADOR:
        return None

    merchant_raw = _limpar_ruido_operacional_nubank(trecho_merchant)
    merchant_norm = normalizar_texto(merchant_raw)
    if not merchant_norm:
        return "indefinido", "indefinido"
    return merchant_raw, merchant_norm


def extrair_merchant_tecnico_estavel(descricao_normalizada: str) -> tuple[str, str] | None:
    """Mantem descricoes tecnicas conhecidas como chaves estaveis."""

    for merchant_tecnico in MERCHANTS_TECNICOS_ESTAVEIS:
        if descricao_normalizada == merchant_tecnico or descricao_normalizada.startswith(
            f"{merchant_tecnico} -"
        ):
            return merchant_tecnico, merchant_tecnico
    if descricao_normalizada == "ajuste de compra no debito":
        return descricao_normalizada, descricao_normalizada
    return None


def extrair_merchant_transferencia_ou_pix(descricao_normalizada: str) -> tuple[str, str] | None:
    """Extrai nome de pessoa em descrições de transferência/Pix com separadores."""

    if not descricao_normalizada or not PADRAO_TRANSFERENCIA_PIX.search(descricao_normalizada):
        return None

    partes = [parte.strip() for parte in descricao_normalizada.split("-") if parte.strip()]
    if len(partes) < 2:
        return None

    for trecho in partes[1:]:
        nome_limpo = _limpar_trecho_nome_transferencia_ou_pix(trecho)
        nome_normalizado = normalizar_texto(nome_limpo)
        if not nome_normalizado or nome_normalizado in TERMOS_INVALIDOS_NOME_TRANSFERENCIA:
            continue
        if not any(caractere.isalpha() for caractere in nome_normalizado):
            continue
        return nome_limpo, nome_normalizado

    return None


def extrair_merchant(descricao_normalizada: str) -> tuple[str, str]:
    """Extrai merchant bruto e normalizado por regra determinística simples."""

    merchant_tecnico = extrair_merchant_tecnico_estavel(descricao_normalizada)
    if merchant_tecnico is not None:
        return merchant_tecnico

    merchant_transferencia_ou_pix = extrair_merchant_transferencia_ou_pix(descricao_normalizada)
    if merchant_transferencia_ou_pix is not None:
        return merchant_transferencia_ou_pix
    if PADRAO_TRANSFERENCIA_PIX.search(descricao_normalizada) and "-" in descricao_normalizada:
        return "indefinido", "indefinido"

    merchant_apos_prefixo = extrair_merchant_apos_prefixo_nubank(descricao_normalizada)
    if merchant_apos_prefixo is not None:
        return merchant_apos_prefixo

    descricao_sem_ruido = remover_ruido_textual(descricao_normalizada)
    if not descricao_sem_ruido:
        return "indefinido", "indefinido"

    tokens = descricao_sem_ruido.split()
    merchant_raw = " ".join(tokens[:4]).strip() or "indefinido"
    merchant_norm = normalizar_texto(merchant_raw)
    return merchant_raw, merchant_norm or "indefinido"


def normalizar_descricao_e_extrair_merchant(descricao_bruta: str) -> DescricaoNormalizada:
    """Executa normalização canônica de descrição e extração inicial de merchant."""

    description_norm = normalizar_texto(descricao_bruta)
    merchant_raw, merchant_norm = extrair_merchant(description_norm)
    return DescricaoNormalizada(
        description_norm=description_norm,
        merchant_raw=merchant_raw,
        merchant_norm=merchant_norm,
    )
