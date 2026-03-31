"""Views do app reports (estrutura inicial do MVP)."""
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def pagina_inicial(request: HttpRequest) -> HttpResponse:
    """Página inicial mínima para validar subida do projeto."""
    contexto = {
        "titulo": "Finance Agent",
        "descricao": "Base inicial do MVP em Django pronta para as próximas fases.",
    }
    return render(request, "pagina_inicial.html", contexto)
