from django.contrib import admin

from .models import CalendarItem


@admin.register(CalendarItem)
class CalendarItemAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "date", "repeat", "owner", "is_done")
    list_filter = ("kind", "repeat", "is_done")
    search_fields = ("title", "owner__email")
    date_hierarchy = "date"
