from django.contrib import admin

from reports.models import Budget


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ("period_month", "category", "planned_amount")
    list_filter = ("period_month", "category")
    search_fields = ("period_month", "notes", "category__name")
    autocomplete_fields = ("category",)
