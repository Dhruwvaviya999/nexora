from django.contrib import admin

from apps.mentions.models import Mention


@admin.register(Mention)
class MentionAdmin(admin.ModelAdmin):
    list_display = ("mentioned_user", "workspace", "comment", "created_at")
    search_fields = ("mentioned_user__email",)
    autocomplete_fields = ("comment", "mentioned_user", "workspace")
    readonly_fields = ("created_at", "updated_at")
