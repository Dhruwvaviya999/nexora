"""Serializers for the AI app. Follow the project's TaskSerializer conventions."""

from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from apps.ai.models import (
    AIConversation,
    AIMessage,
    AISettings,
    PromptTemplate,
    SearchHistory,
)
from apps.ai.services import crypto


class AIMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIMessage
        fields = (
            "id",
            "conversation",
            "role",
            "content",
            "sources",
            "token_count",
            "created_at",
        )
        read_only_fields = fields


class AIConversationSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    message_count = serializers.IntegerField(source="messages.count", read_only=True)

    class Meta:
        model = AIConversation
        fields = (
            "id",
            "workspace",
            "user",
            "title",
            "message_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class AIConversationDetailSerializer(AIConversationSerializer):
    messages = AIMessageSerializer(many=True, read_only=True)

    class Meta(AIConversationSerializer.Meta):
        fields = AIConversationSerializer.Meta.fields + ("messages",)


class SearchHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchHistory
        fields = (
            "id",
            "workspace",
            "query",
            "results_count",
            "top_score",
            "created_at",
        )
        read_only_fields = fields


class PromptTemplateSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = PromptTemplate
        fields = (
            "id",
            "workspace",
            "name",
            "description",
            "category",
            "template",
            "is_shared",
            "created_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_by", "created_at", "updated_at")


class AISettingsSerializer(serializers.ModelSerializer):
    # API key is write-only; reads expose only whether one is set.
    api_key = serializers.CharField(
        write_only=True, required=False, allow_blank=True
    )
    has_api_key = serializers.BooleanField(read_only=True)

    class Meta:
        model = AISettings
        fields = (
            "id",
            "workspace",
            "is_enabled",
            "provider",
            "chat_model",
            "embedding_provider",
            "embedding_model",
            "temperature",
            "max_tokens",
            "api_key",
            "has_api_key",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "workspace", "has_api_key", "created_at", "updated_at")

    def validate_temperature(self, value):
        if not 0.0 <= value <= 2.0:
            raise serializers.ValidationError("Temperature must be between 0 and 2.")
        return value

    def validate_max_tokens(self, value):
        if not 1 <= value <= 8192:
            raise serializers.ValidationError("max_tokens must be between 1 and 8192.")
        return value

    def update(self, instance, validated_data):
        # Encrypt + store the API key out of band; never keep plaintext.
        if "api_key" in validated_data:
            raw = validated_data.pop("api_key")
            instance.api_key_encrypted = crypto.encrypt(raw) if raw else ""
        return super().update(instance, validated_data)


# ---- Request serializers for the action endpoints (validation + OpenAPI) ----

class ChatRequestSerializer(serializers.Serializer):
    workspace = serializers.UUIDField()
    conversation = serializers.UUIDField(required=False, allow_null=True)
    message = serializers.CharField(max_length=8000)


class SearchRequestSerializer(serializers.Serializer):
    workspace = serializers.UUIDField()
    query = serializers.CharField(max_length=1000)
    limit = serializers.IntegerField(required=False, min_value=1, max_value=20)


class SummarizeRequestSerializer(serializers.Serializer):
    workspace = serializers.UUIDField()
    target_type = serializers.ChoiceField(
        choices=("project", "task", "document", "activity")
    )
    target_id = serializers.UUIDField(required=False, allow_null=True)
    period = serializers.ChoiceField(
        choices=("day", "week", "month"), required=False, default="week"
    )


class GenerateTasksRequestSerializer(serializers.Serializer):
    workspace = serializers.UUIDField()
    document = serializers.UUIDField(required=False, allow_null=True)
    text = serializers.CharField(required=False, allow_blank=True, max_length=8000)

    def validate(self, attrs):
        if not attrs.get("document") and not attrs.get("text"):
            raise serializers.ValidationError(
                "Provide either a document id or text."
            )
        return attrs
