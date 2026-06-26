"""Workspace serializers."""

from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from apps.workspaces.models import Workspace, WorkspaceMember


class WorkspaceMemberSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = WorkspaceMember
        fields = ("id", "user", "role", "joined_at")
        read_only_fields = fields


class WorkspaceSerializer(serializers.ModelSerializer):
    """Read/write serializer for workspaces.

    ``slug`` and ``owner`` are derived server-side. ``role`` reflects the
    requesting user's role in the workspace; ``member_count`` is a convenience
    for list views.
    """

    owner = UserSerializer(read_only=True)
    role = serializers.SerializerMethodField()
    member_count = serializers.IntegerField(source="members.count", read_only=True)

    class Meta:
        model = Workspace
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "owner",
            "role",
            "member_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "slug", "owner", "created_at", "updated_at")

    def get_role(self, obj) -> str | None:
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        member = obj.members.filter(user=request.user).first()
        return member.role if member else None
