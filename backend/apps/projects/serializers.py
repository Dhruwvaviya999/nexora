from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from apps.projects.models import Project


class ProjectSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    created_by = UserSerializer(read_only=True)
    updated_by = UserSerializer(read_only=True)
    task_count = serializers.IntegerField(source="tasks.count", read_only=True)

    class Meta:
        model = Project
        fields = (
            "id",
            "workspace",
            "name",
            "slug",
            "description",
            "color",
            "status",
            "archived",
            "owner",
            "task_count",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "slug",
            "owner",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        )

    def create(self, validated_data):
        # The creator owns the project by default.
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data.setdefault("owner", request.user)
        return super().create(validated_data)
