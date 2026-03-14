"""Mapeamento de rotas do projeto Finance Agent."""
from django.contrib import admin
from django.urls import path

from reports.views import pagina_inicial

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", pagina_inicial, name="pagina_inicial"),
]
