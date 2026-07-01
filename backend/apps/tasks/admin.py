from django.contrib import admin

from apps.tasks.models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "status", "priority", "assignee", "due_date")
    list_filter = ("status", "priority")
    search_fields = ("title", "description", "project__name")
    autocomplete_fields = ("workspace", "project", "assignee", "reporter")
    readonly_fields = ("created_by", "updated_by", "created_at", "updated_at")
