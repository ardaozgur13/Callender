from django.contrib import admin

from .models import FoodItem, ShelfLifeRule


@admin.register(ShelfLifeRule)
class ShelfLifeRuleAdmin(admin.ModelAdmin):
    list_display = ("name_tr", "category", "storage", "opened_days", "source")
    list_filter = ("category", "source", "storage")
    search_fields = ("name_tr", "key")


@admin.register(FoodItem)
class FoodItemAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "family", "storage", "opened_on", "package_expiry", "use_by", "is_consumed")
    list_filter = ("storage", "is_consumed")
    search_fields = ("name", "owner__email")
    readonly_fields = ("use_by",)
