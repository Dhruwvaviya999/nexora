from django.contrib import admin

from apps.projects.models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "workspace", "status", "archived", "owner", "created_at")
    list_filter = ("status", "archived")
    search_fields = ("name", "description", "workspace__name")
    autocomplete_fields = ("workspace", "owner")
    readonly_fields = ("created_by", "updated_by", "created_at", "updated_at")
