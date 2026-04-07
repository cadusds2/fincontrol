"""Funções de normalização textual usadas na importação."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

PADRAO_RUIDO = re.compile(
    r"\b(?:estorno\s+compra\s+no\s+(?:credito|debito)|compra\s+no\s+(?:credito|debito)|debito|credito|pix|cp\s+\d+)\b"
)
PADRAO_ESPACOS = re.compile(r"\s+")
PADRAO_NAO_ALFANUMERICO = re.compile(r"[^\w\s/&.-]")
PADRAO_CPF_CNPJ_MASCARADO = re.compile(
    r"(?:\d{3}\.?\*{3}\.?\*{3}-?\d{2}|\*{3}\.?\*{3}\.?\*{3}-?\*{2})",
    flags=re.IGNORECASE,
)
PADRAO_TERMO_BANCARIO = re.compile(r"\b(?:banco|ag(?:encia)?|conta|cc)\b")
PADRAO_NUMERO_ISOLADO = re.compile(r"\b[\d.*./-]+\b")
PADRAO_DOCUMENTO_ROTULADO = re.compile(
    r"\b(?:cpf|cnpj)\s*[:.-]?\s*[\d*./-]+",
    flags=re.IGNORECASE,
)
PADRAO_CODIGO_EM_PARENTESES = re.compile(r"\([^)]*\)")
PADRAO_BLOCO_BANCARIO = re.compile(
    r"(?:^|[\s-])(?:banco|ag(?:encia)?|conta|cc)\s*[:.-]?\s*[\w./-]*"
)
PADRAO_SEQUENCIA_NUMERICA_IRRELEVANTE = re.compile(r"\b\d+(?:[./-]\d+)*\b")
PADRAO_TRANSFERENCIA_PIX = re.compile(r"\b(?:transferencia|pix)\b")
PADRAO_COMPRA_DEBITO_CREDITO = re.compile(r"\b(?:compra|estorno\s+compra)\b.*\b(?:debito|credito)\b")
PADRAO_ASSINATURA_GATEWAY = re.compile(r"\b(?:dm|mp|pagseguro|mercado\s*pago|picpay|stripe)\b")
PADRAO_PREFIXO_GATEWAY = re.compile(r"^(?:dm|mp)\s*[*-]?\s*")
TERMOS_INVALIDOS_NOME_TRANSFERENCIA = {
    "pix",
    "transferencia",
    "transferencia recebida pelo pix",
    "transferencia enviada pelo pix",
    "recebida",
    "enviada",
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


def sanear_trecho_merchant(trecho: str) -> str:
    """Remove sufixos bancários e identificadores não comerciais de um trecho."""

    trecho_saneado = PADRAO_CODIGO_EM_PARENTESES.sub(" ", trecho or "")
    trecho_saneado = PADRAO_DOCUMENTO_ROTULADO.sub(" ", trecho_saneado)
    trecho_saneado = PADRAO_CPF_CNPJ_MASCARADO.sub(" ", trecho_saneado)
    trecho_saneado = PADRAO_BLOCO_BANCARIO.sub(" ", trecho_saneado)
    trecho_saneado = PADRAO_SEQUENCIA_NUMERICA_IRRELEVANTE.sub(" ", trecho_saneado)
    trecho_saneado = PADRAO_ESPACOS.sub(" ", trecho_saneado).strip(" -/")
    return trecho_saneado or "indefinido"


def _limpar_trecho_nome_transferencia_ou_pix(trecho: str) -> str:
    """Remove lixo comum do trecho de nome em transferência/Pix."""

    trecho_limpo = sanear_trecho_merchant(trecho)
    trecho_limpo = PADRAO_TERMO_BANCARIO.sub(" ", trecho_limpo)
    trecho_limpo = PADRAO_NUMERO_ISOLADO.sub(" ", trecho_limpo)
    trecho_limpo = PADRAO_ESPACOS.sub(" ", trecho_limpo).strip(" -")
    return trecho_limpo


def extrair_merchant_transferencia_pix(descricao_normalizada: str) -> tuple[str, str] | None:
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


def extrair_merchant_compra_debito_credito(descricao_normalizada: str) -> tuple[str, str] | None:
    """Extrai merchant de descrições de compra em débito/crédito."""

    if not descricao_normalizada or not PADRAO_COMPRA_DEBITO_CREDITO.search(descricao_normalizada):
        return None

    descricao_sem_ruido = remover_ruido_textual(descricao_normalizada)
    if not descricao_sem_ruido:
        return None

    merchant_raw = sanear_trecho_merchant(descricao_sem_ruido)
    merchant_norm = normalizar_texto(merchant_raw)
    if not merchant_norm:
        return None
    return merchant_raw, merchant_norm


def extrair_merchant_assinatura_gateway(descricao_normalizada: str) -> tuple[str, str] | None:
    """Extrai merchant para descrições de assinatura mediadas por gateway."""

    if not descricao_normalizada or not PADRAO_ASSINATURA_GATEWAY.search(descricao_normalizada):
        return None

    descricao_sem_ruido = remover_ruido_textual(descricao_normalizada)
    if not descricao_sem_ruido:
        return None

    merchant_raw = PADRAO_PREFIXO_GATEWAY.sub("", descricao_sem_ruido).strip(" -")
    merchant_raw = sanear_trecho_merchant(merchant_raw)
    merchant_norm = normalizar_texto(merchant_raw)
    if not merchant_norm:
        return None
    return merchant_raw, merchant_norm


def extrair_merchant_contextual(descricao_normalizada: str) -> tuple[str, str]:
    """Orquestra cadeia de extratores especializados em ordem determinística."""

    extratores = (
        extrair_merchant_transferencia_pix,
        extrair_merchant_compra_debito_credito,
        extrair_merchant_assinatura_gateway,
    )

    for extrator in extratores:
        merchant_extraido = extrator(descricao_normalizada)
        if merchant_extraido is not None:
            return merchant_extraido

    descricao_sem_ruido = remover_ruido_textual(descricao_normalizada)
    if not descricao_sem_ruido:
        return "indefinido", "indefinido"

    tokens = descricao_sem_ruido.split()
    merchant_raw = " ".join(tokens[:4]).strip() or "indefinido"
    merchant_norm = normalizar_texto(merchant_raw)
    return merchant_raw, merchant_norm or "indefinido"


def extrair_merchant(descricao_normalizada: str) -> tuple[str, str]:
    """Extrai merchant mantendo compatibilidade da API antiga."""

    if PADRAO_TRANSFERENCIA_PIX.search(descricao_normalizada) and "-" in descricao_normalizada:
        merchant_transferencia_pix = extrair_merchant_transferencia_pix(descricao_normalizada)
        if merchant_transferencia_pix is None:
            return "indefinido", "indefinido"
    return extrair_merchant_contextual(descricao_normalizada)


def normalizar_descricao_e_extrair_merchant(descricao_bruta: str) -> DescricaoNormalizada:
    """Executa normalização canônica de descrição e extração inicial de merchant."""

    description_norm = normalizar_texto(descricao_bruta)
    merchant_raw, merchant_norm = extrair_merchant(description_norm)
    return DescricaoNormalizada(
        description_norm=description_norm,
        merchant_raw=merchant_raw,
        merchant_norm=merchant_norm,
    )
