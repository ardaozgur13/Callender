from django.contrib import admin

from .models import Chore, ChoreLog, HomeStatus


@admin.register(Chore)
class ChoreAdmin(admin.ModelAdmin):
    list_display = ("title", "family", "assigned_to", "weekday", "is_active")
    list_filter = ("is_active", "weekday")
    search_fields = ("title",)


@admin.register(ChoreLog)
class ChoreLogAdmin(admin.ModelAdmin):
    list_display = ("chore", "date", "done_by", "done_at")


@admin.register(HomeStatus)
class HomeStatusAdmin(admin.ModelAdmin):
    list_display = ("family", "kind", "status", "updated_by", "updated_at")
