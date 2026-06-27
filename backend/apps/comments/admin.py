from django.contrib import admin

from apps.comments.models import Comment


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("author", "content_type", "object_id", "is_edited", "is_deleted", "created_at")
    list_filter = ("is_deleted", "is_edited", "content_type")
    search_fields = ("content", "author__email")
    autocomplete_fields = ("workspace", "author", "parent")
    readonly_fields = ("created_at", "updated_at")
