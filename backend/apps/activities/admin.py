from django.contrib import admin

from apps.activities.models import Activity


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ("action", "actor", "workspace", "created_at")
    list_filter = ("action",)
    search_fields = ("action", "actor__email")
    readonly_fields = ("created_at", "updated_at")
