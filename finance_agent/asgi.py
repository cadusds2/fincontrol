"""Configuração ASGI do projeto Finance Agent."""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "finance_agent.settings")

application = get_asgi_application()
