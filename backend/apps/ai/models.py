"""
AI app models — the generation layer.

* AIConversation / AIMessage — chat history (workspace-scoped, owned by a user).
* AISettings — per-workspace provider configuration (admin-managed; the API key
  is stored encrypted, see apps.ai.services.crypto).
* SearchHistory — recent semantic-search queries (for "recent queries" UI).
* PromptTemplate — reusable saved prompts (the prompt library).
"""

from django.conf import settings
from django.db import models

from apps.common.models import BaseModel, WorkspaceScopedModel


class AIConversation(WorkspaceScopedModel):
    """A chat thread between a user and the workspace assistant."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_conversations",
    )
    title = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ("-updated_at",)
        indexes = [models.Index(fields=["workspace", "user", "-updated_at"])]

    def __str__(self) -> str:
        return self.title or f"Conversation {self.pk}"


class MessageRole(models.TextChoices):
    USER = "user", "User"
    ASSISTANT = "assistant", "Assistant"
    SYSTEM = "system", "System"


class AIMessage(BaseModel):
    """A single message in a conversation. ``sources`` holds retrieved context."""

    conversation = models.ForeignKey(
        AIConversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=16, choices=MessageRole.choices)
    content = models.TextField()
    # Retrieved chunks/records cited by an assistant reply (list of dicts).
    sources = models.JSONField(default=list, blank=True)
    token_count = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("created_at",)
        indexes = [models.Index(fields=["conversation", "created_at"])]

    def __str__(self) -> str:
        return f"{self.role}: {self.content[:40]}"


class AISettings(BaseModel):
    """Per-workspace AI configuration. One row per workspace."""

    workspace = models.OneToOneField(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="ai_settings",
    )
    is_enabled = models.BooleanField(default=True)

    provider = models.CharField(max_length=32, default="gemini")
    chat_model = models.CharField(max_length=128, default="gemini-2.0-flash")
    embedding_provider = models.CharField(
        max_length=32, default="sentence_transformer"
    )
    embedding_model = models.CharField(max_length=128, default="all-MiniLM-L6-v2")

    temperature = models.FloatField(default=0.2)
    max_tokens = models.PositiveIntegerField(default=1024)

    # Fernet-encrypted at rest (see services.crypto). Never exposed in plaintext.
    api_key_encrypted = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "AI settings"
        verbose_name_plural = "AI settings"

    def __str__(self) -> str:
        return f"AISettings({self.workspace_id}, {self.provider})"

    @property
    def has_api_key(self) -> bool:
        return bool(self.api_key_encrypted)


class SearchHistory(BaseModel):
    """A logged semantic-search query (workspace + user scoped)."""

    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="search_history",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_search_history",
    )
    query = models.CharField(max_length=1000)
    results_count = models.PositiveIntegerField(default=0)
    top_score = models.FloatField(default=0.0)

    class Meta:
        ordering = ("-created_at",)
        verbose_name_plural = "search history"
        indexes = [models.Index(fields=["workspace", "user", "-created_at"])]

    def __str__(self) -> str:
        return self.query[:60]


class PromptTemplate(WorkspaceScopedModel):
    """A reusable saved prompt (the prompt library)."""

    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, default="")
    category = models.CharField(max_length=64, blank=True, default="general")
    template = models.TextField()
    # Shared templates are visible to the whole workspace; otherwise author-only.
    is_shared = models.BooleanField(default=True)

    class Meta:
        ordering = ("name",)
        indexes = [models.Index(fields=["workspace", "category"])]

    def __str__(self) -> str:
        return self.name
