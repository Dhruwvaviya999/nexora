from django.contrib import admin

from apps.ai.models import (
    AIConversation,
    AIMessage,
    AISettings,
    PromptTemplate,
    SearchHistory,
)


class AIMessageInline(admin.TabularInline):
    model = AIMessage
    extra = 0
    fields = ("role", "content", "created_at")
    readonly_fields = ("created_at",)


@admin.register(AIConversation)
class AIConversationAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "workspace", "updated_at")
    list_filter = ("workspace",)
    search_fields = ("title", "user__email")
    raw_id_fields = ("workspace", "user")
    inlines = [AIMessageInline]


@admin.register(AISettings)
class AISettingsAdmin(admin.ModelAdmin):
    list_display = ("workspace", "provider", "chat_model", "is_enabled", "has_api_key")
    list_filter = ("provider", "is_enabled")
    # Never surface the encrypted key in the admin form.
    exclude = ("api_key_encrypted",)
    raw_id_fields = ("workspace",)

    @admin.display(boolean=True, description="API key set")
    def has_api_key(self, obj):
        return obj.has_api_key


@admin.register(SearchHistory)
class SearchHistoryAdmin(admin.ModelAdmin):
    list_display = ("query", "user", "workspace", "results_count", "created_at")
    list_filter = ("workspace",)
    search_fields = ("query",)
    raw_id_fields = ("workspace", "user")


@admin.register(PromptTemplate)
class PromptTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "workspace", "is_shared", "created_at")
    list_filter = ("category", "is_shared", "workspace")
    search_fields = ("name", "description", "template")
    raw_id_fields = ("workspace",)
