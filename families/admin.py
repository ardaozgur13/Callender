from django.contrib import admin

from .models import Family, FamilyMember


class FamilyMemberInline(admin.TabularInline):
    model = FamilyMember
    extra = 0


@admin.register(Family)
class FamilyAdmin(admin.ModelAdmin):
    list_display = ("name", "invite_code", "created_by", "created_at")
    search_fields = ("name", "invite_code")
    inlines = [FamilyMemberInline]
