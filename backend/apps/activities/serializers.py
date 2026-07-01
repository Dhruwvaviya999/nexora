from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from apps.activities.models import Activity


class ActivitySerializer(serializers.ModelSerializer):
    actor = UserSerializer(read_only=True)
    target_type = serializers.SerializerMethodField()

    class Meta:
        model = Activity
        fields = (
            "id",
            "actor",
            "action",
            "target_type",
            "object_id",
            "metadata",
            "workspace",
            "created_at",
        )
        read_only_fields = fields

    def get_target_type(self, obj) -> str | None:
        return obj.content_type.model if obj.content_type_id else None
