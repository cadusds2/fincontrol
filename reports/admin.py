"""Admin do app reports."""

from django.contrib import admin

from .models import Budget


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ("period_month", "category", "planned_amount", "created_at")
    list_filter = ("period_month", "category")
    search_fields = ("period_month", "category__name", "notes")
    autocomplete_fields = ("category",)
