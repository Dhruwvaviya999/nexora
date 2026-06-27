from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from apps.invitations.models import INVITABLE_ROLES, Invitation, InvitationStatus
from apps.workspaces.models import WorkspaceMember


class InvitationSerializer(serializers.ModelSerializer):
    invited_by = UserSerializer(read_only=True)
    workspace_name = serializers.CharField(source="workspace.name", read_only=True)

    class Meta:
        model = Invitation
        fields = (
            "id",
            "workspace",
            "workspace_name",
            "email",
            "role",
            "status",
            "token",
            "invited_by",
            "expires_at",
            "created_at",
        )
        # token is the accept/reject credential; only ever returned to the
        # scoped audience (workspace admins and the invited email).
        read_only_fields = (
            "id",
            "status",
            "token",
            "invited_by",
            "expires_at",
            "created_at",
        )

    def validate_email(self, value: str) -> str:
        return value.lower().strip()

    def validate_role(self, value: str) -> str:
        if value not in INVITABLE_ROLES:
            raise serializers.ValidationError("Members can only be invited as admin or member.")
        return value

    def validate(self, attrs):
        workspace = attrs["workspace"]
        email = attrs["email"]

        if WorkspaceMember.objects.filter(
            workspace=workspace, user__email__iexact=email
        ).exists():
            raise serializers.ValidationError(
                {"email": "That person is already a member of this workspace."}
            )
        if Invitation.objects.filter(
            workspace=workspace, email__iexact=email, status=InvitationStatus.PENDING
        ).exists():
            raise serializers.ValidationError(
                {"email": "There is already a pending invitation for this email."}
            )
        return attrs
