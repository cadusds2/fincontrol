"""Funções de normalização textual usadas na importação."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

PADRAO_RUIDO = re.compile(r"\b(?:compra\s+no\s+credito|debito|credito|pix|cp\s+\d+)\b")
PADRAO_ESPACOS = re.compile(r"\s+")
PADRAO_NAO_ALFANUMERICO = re.compile(r"[^\w\s/&.-]")


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


def extrair_merchant(descricao_normalizada: str) -> tuple[str, str]:
    """Extrai merchant bruto e normalizado por regra determinística simples."""

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
