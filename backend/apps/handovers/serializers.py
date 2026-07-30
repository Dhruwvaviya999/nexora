from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from apps.handovers.models import Handover, HandoverStatus
from apps.tasks.models import Task


class HandoverSerializer(serializers.ModelSerializer):
    # `workspace` is derived from the task, never set directly by clients.
    workspace = serializers.PrimaryKeyRelatedField(read_only=True)
    from_user = UserSerializer(read_only=True)
    to_user = UserSerializer(read_only=True)
    reviewer = UserSerializer(read_only=True)
    created_by = UserSerializer(read_only=True)
    updated_by = UserSerializer(read_only=True)

    # Write-only id inputs for the relational fields.
    task = serializers.PrimaryKeyRelatedField(queryset=Task.objects.all())
    to_user_id = serializers.UUIDField(write_only=True)

    # Convenience read fields so lists don't need extra requests.
    task_title = serializers.CharField(source="task.title", read_only=True)
    project_id = serializers.UUIDField(source="task.project_id", read_only=True)

    class Meta:
        model = Handover
        fields = (
            "id",
            "workspace",
            "task",
            "task_title",
            "project_id",
            "from_user",
            "to_user",
            "to_user_id",
            "summary",
            "pending_items",
            "resources",
            "status",
            "reviewer",
            "review_comment",
            "reviewed_at",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "workspace",
            "from_user",
            "to_user",
            "status",
            "reviewer",
            "review_comment",
            "reviewed_at",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        request = self.context.get("request")

        if self.instance is not None:
            # Edits are only allowed while the handover awaits review, and the
            # task itself can never be swapped out after submission.
            if self.instance.status != HandoverStatus.PENDING:
                raise serializers.ValidationError(
                    "Only pending handovers can be edited."
                )
            task = attrs.get("task")
            if task is not None and task.pk != self.instance.task_id:
                raise serializers.ValidationError(
                    {"task": "The task of a handover can't be changed."}
                )
            attrs.pop("task", None)
            workspace = self.instance.workspace
        else:
            task = attrs.get("task")
            if task is None:
                raise serializers.ValidationError({"task": "This field is required."})
            # Derive workspace from the task (keeps the two consistent).
            workspace = task.workspace
            attrs["workspace"] = workspace

        if "to_user_id" in attrs:
            to_user_id = attrs.pop("to_user_id")
            member = (
                workspace.members.filter(user_id=to_user_id)
                .select_related("user")
                .first()
            )
            if member is None:
                raise serializers.ValidationError(
                    {"to_user_id": "User is not a member of this workspace."}
                )
            if request and member.user_id == request.user.pk:
                raise serializers.ValidationError(
                    {"to_user_id": "You can't hand a task over to yourself."}
                )
            attrs["to_user"] = member.user

        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        if request:
            validated_data["from_user"] = request.user
        return super().create(validated_data)


class HandoverReviewSerializer(serializers.Serializer):
    """Input for the review action: a decision plus an optional comment."""

    decision = serializers.ChoiceField(
        choices=(HandoverStatus.APPROVED, HandoverStatus.REJECTED)
    )
    comment = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=5000
    )

    def validate(self, attrs):
        if attrs["decision"] == HandoverStatus.REJECTED and not attrs.get("comment"):
            raise serializers.ValidationError(
                {"comment": "A comment is required when rejecting a handover."}
            )
        return attrs
