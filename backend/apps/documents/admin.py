from django.contrib import admin

from apps.documents.models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "workspace", "project", "file_type", "file_size", "uploaded_by")
    list_filter = ("file_type",)
    search_fields = ("title", "description")
    autocomplete_fields = ("workspace", "project", "uploaded_by")
    readonly_fields = ("file_size", "file_type", "created_by", "updated_by", "created_at", "updated_at")
