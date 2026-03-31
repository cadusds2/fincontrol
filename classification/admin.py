"""Admin do app classification."""

from django.contrib import admin

from .models import Category, MerchantMap, ReviewQueue


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "kind", "is_reportable", "is_active")
    list_filter = ("kind", "is_reportable", "is_active")
    search_fields = ("name", "slug", "description")


@admin.register(MerchantMap)
class MerchantMapAdmin(admin.ModelAdmin):
    list_display = ("merchant_norm", "category", "source", "confidence", "usage_count", "last_used_at")
    list_filter = ("source", "category")
    search_fields = ("merchant_norm", "category__name")
    autocomplete_fields = ("category",)


@admin.register(ReviewQueue)
class ReviewQueueAdmin(admin.ModelAdmin):
    list_display = ("transaction", "reason", "status", "suggested_category", "created_at", "resolved_at")
    list_filter = ("reason", "status", "created_at")
    search_fields = (
        "transaction__description_raw",
        "transaction__merchant_norm",
        "resolution_note",
    )
    autocomplete_fields = ("transaction", "suggested_category")
