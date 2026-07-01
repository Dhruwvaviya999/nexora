from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from apps.projects.models import Project
from apps.tasks.models import Task


class TaskSerializer(serializers.ModelSerializer):
    # `workspace` is derived from the project, never set directly by clients.
    workspace = serializers.PrimaryKeyRelatedField(read_only=True)
    assignee = UserSerializer(read_only=True)
    reporter = UserSerializer(read_only=True)
    created_by = UserSerializer(read_only=True)
    updated_by = UserSerializer(read_only=True)

    # Write-only id inputs for the relational fields.
    project = serializers.PrimaryKeyRelatedField(queryset=Project.objects.all())
    assignee_id = serializers.UUIDField(
        write_only=True, required=False, allow_null=True
    )
    reporter_id = serializers.UUIDField(
        write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = Task
        fields = (
            "id",
            "workspace",
            "project",
            "title",
            "description",
            "status",
            "priority",
            "assignee",
            "assignee_id",
            "reporter",
            "reporter_id",
            "due_date",
            "start_date",
            "estimated_hours",
            "labels",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "workspace",
            "assignee",
            "reporter",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        )

    def _resolve_member(self, workspace, user_id, field):
        """Validate that an assignee/reporter is a member of the workspace."""
        if user_id is None:
            return None
        member = workspace.members.filter(user_id=user_id).select_related("user").first()
        if member is None:
            raise serializers.ValidationError(
                {field: "User is not a member of this workspace."}
            )
        return member.user

    def validate(self, attrs):
        project = attrs.get("project") or getattr(self.instance, "project", None)
        if project is None:
            raise serializers.ValidationError({"project": "This field is required."})

        # Derive workspace from the project (keeps the two consistent).
        attrs["workspace"] = project.workspace

        if "assignee_id" in attrs:
            attrs["assignee"] = self._resolve_member(
                project.workspace, attrs.pop("assignee_id"), "assignee_id"
            )
        if "reporter_id" in attrs:
            attrs["reporter"] = self._resolve_member(
                project.workspace, attrs.pop("reporter_id"), "reporter_id"
            )
        return attrs

    def create(self, validated_data):
        # Default the reporter to the creating user when not provided.
        request = self.context.get("request")
        if "reporter" not in validated_data and request:
            validated_data["reporter"] = request.user
        return super().create(validated_data)
