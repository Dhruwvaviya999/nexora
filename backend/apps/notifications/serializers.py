from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from apps.notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    actor = UserSerializer(read_only=True)

    class Meta:
        model = Notification
        fields = (
            "id",
            "type",
            "title",
            "message",
            "link",
            "is_read",
            "actor",
            "workspace",
            "created_at",
        )
        read_only_fields = fields
