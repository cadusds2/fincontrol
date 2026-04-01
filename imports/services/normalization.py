"""Funções de normalização textual usadas na importação."""

from __future__ import annotations

import unicodedata


def normalizar_texto(texto: str) -> str:
    """Normaliza texto para forma estável no contexto do MVP."""

    texto_limpo = unicodedata.normalize("NFKD", texto or "")
    texto_limpo = "".join(char for char in texto_limpo if not unicodedata.combining(char))
    return " ".join(texto_limpo.lower().split())


def extrair_merchant(descricao_normalizada: str) -> str:
    """Extrai um identificador simples de merchant a partir da descrição."""

    return " ".join(descricao_normalizada.split()[:3]).strip() or "indefinido"
