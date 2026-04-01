"""Admin do app reports."""

from django.contrib import admin

from .models import Budget


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ("period_month", "category", "planned_amount", "updated_at")
    list_filter = ("period_month", "category", "category__kind")
    search_fields = ("period_month", "category__name", "notes")
    autocomplete_fields = ("category",)
    list_select_related = ("category",)
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-period_month", "category__name")
    list_per_page = 50
