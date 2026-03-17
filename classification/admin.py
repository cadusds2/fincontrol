from django.contrib import admin

from classification.models import Category, MerchantMap, ReviewQueue


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "kind", "is_reportable", "is_active")
    list_filter = ("kind", "is_reportable", "is_active")
    search_fields = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(MerchantMap)
class MerchantMapAdmin(admin.ModelAdmin):
    list_display = ("merchant_norm", "category", "source", "confidence", "usage_count", "last_used_at")
    list_filter = ("source", "category")
    search_fields = ("merchant_norm",)
    autocomplete_fields = ("category",)


@admin.register(ReviewQueue)
class ReviewQueueAdmin(admin.ModelAdmin):
    list_display = ("id", "transaction", "reason", "status", "suggested_category", "created_at", "resolved_at")
    list_filter = ("reason", "status", "suggested_category")
    search_fields = ("transaction__description_raw", "resolution_note")
    autocomplete_fields = ("transaction", "suggested_category")
