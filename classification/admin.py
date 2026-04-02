"""Admin do app classification."""

from django.contrib import admin

from .models import Category, MerchantMap, ReviewQueue


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "kind", "is_reportable", "is_active", "updated_at")
    list_filter = ("kind", "is_reportable", "is_active")
    search_fields = ("name", "slug", "description")
    ordering = ("name",)
    readonly_fields = ("created_at", "updated_at")
    list_per_page = 50


@admin.register(MerchantMap)
class MerchantMapAdmin(admin.ModelAdmin):
    list_display = (
        "merchant_norm",
        "category",
        "source",
        "confidence",
        "usage_count",
        "last_used_at",
    )
    list_filter = ("source", "category", "category__kind")
    search_fields = ("merchant_norm", "category__name")
    autocomplete_fields = ("category",)
    list_select_related = ("category",)
    list_editable = ("category", "source", "confidence")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("merchant_norm",)
    list_per_page = 100


@admin.register(ReviewQueue)
class ReviewQueueAdmin(admin.ModelAdmin):
    actions = ("marcar_como_ignorada",)
    list_display = (
        "transaction",
        "reason",
        "status",
        "suggested_category",
        "created_at",
        "resolved_at",
    )
    list_filter = ("reason", "status", "created_at", "suggested_category__kind")
    search_fields = (
        "transaction__description_raw",
        "transaction__merchant_norm",
        "resolution_note",
    )
    autocomplete_fields = ("transaction", "suggested_category")
    list_select_related = ("transaction", "suggested_category")
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    list_per_page = 100

    @admin.action(description="Marcar pendências selecionadas como ignoradas")
    def marcar_como_ignorada(self, request, queryset):
        queryset.filter(status=ReviewQueue.Status.PENDING).update(status=ReviewQueue.Status.IGNORED)
