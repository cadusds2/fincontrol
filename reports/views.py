"""Views do app de relatórios (estrutura inicial do MVP)."""
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def pagina_inicial(request: HttpRequest) -> HttpResponse:
    contexto = {
        "titulo": "Finance Agent",
        "descricao": "Estrutura inicial do MVP em Django está ativa.",
    }
    return render(request, "pagina_inicial.html", contexto)
