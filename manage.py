#!/usr/bin/env python3
"""Ponto de entrada de comandos administrativos do Django."""
import os
import sys


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "finance_agent.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django não está disponível. Instale as dependências do projeto."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
