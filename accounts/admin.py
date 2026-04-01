"""Admin do app accounts."""

from django.contrib import admin

from .models import Account


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = (
        "display_name",
        "bank_name",
        "account_type",
        "is_active",
        "updated_at",
    )
    list_filter = ("bank_name", "account_type", "is_active")
    search_fields = ("display_name", "bank_name", "external_ref")
    ordering = ("bank_name", "display_name")
    list_per_page = 50
    readonly_fields = ("created_at", "updated_at")
