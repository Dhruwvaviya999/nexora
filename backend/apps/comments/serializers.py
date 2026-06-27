"""Comment serializer + the set of resource types that accept comments."""

from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from apps.comments.models import Comment

# Maps the public ``target_type`` value -> ContentType natural key
# (app_label, model). Whitelisting keeps comments off arbitrary tables.
ALLOWED_TARGETS = {
    "project": ("projects", "project"),
    "task": ("tasks", "task"),
    "document": ("documents", "document"),
}


class CommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    reply_count = serializers.IntegerField(source="replies.count", read_only=True)

    # Write-only target selectors (ignored when replying — the parent's target
    # is inherited). Resolved to content_type/object_id in the view.
    target_type = serializers.ChoiceField(
        choices=sorted(ALLOWED_TARGETS), write_only=True, required=False
    )
    target_id = serializers.UUIDField(write_only=True, required=False)

    parent = serializers.PrimaryKeyRelatedField(
        queryset=Comment.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = Comment
        fields = (
            "id",
            "content",
            "author",
            "parent",
            "target_type",
            "target_id",
            "reply_count",
            "is_edited",
            "is_deleted",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "author",
            "reply_count",
            "is_edited",
            "is_deleted",
            "created_at",
            "updated_at",
        )

    def validate_content(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Comment cannot be empty.")
        return value

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.is_deleted:
            data["content"] = "[deleted]"
        return data
