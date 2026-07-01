from django.contrib import admin

from apps.knowledge.models import DocumentChunk, EmbeddingJob


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = ("document", "chunk_index", "token_count", "workspace", "created_at")
    list_filter = ("workspace",)
    search_fields = ("content", "document__title")
    # The embedding vector is large and unhelpful in the form.
    exclude = ("embedding",)
    raw_id_fields = ("workspace", "document")


@admin.register(EmbeddingJob)
class EmbeddingJobAdmin(admin.ModelAdmin):
    list_display = (
        "document",
        "status",
        "chunk_count",
        "provider",
        "model",
        "created_at",
    )
    list_filter = ("status", "provider", "workspace")
    search_fields = ("document__title", "error")
    raw_id_fields = ("workspace", "document")
    readonly_fields = ("started_at", "finished_at")
