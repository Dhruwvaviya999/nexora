"""Mention serializer (read-only API of 'who mentioned me')."""

from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from apps.mentions.models import Mention


class MentionSerializer(serializers.ModelSerializer):
    mentioned_user = UserSerializer(read_only=True)
    actor = serializers.SerializerMethodField()
    comment_excerpt = serializers.SerializerMethodField()

    class Meta:
        model = Mention
        fields = (
            "id",
            "comment",
            "comment_excerpt",
            "actor",
            "mentioned_user",
            "workspace",
            "created_at",
        )
        read_only_fields = fields

    def get_actor(self, obj):
        return UserSerializer(obj.comment.author).data

    def get_comment_excerpt(self, obj) -> str:
        return (obj.comment.content or "")[:140]
