"""Workspace invitation API."""

from django.contrib.auth import get_user_model
from django.db.models import Q
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.activities.services import log_activity
from apps.invitations.models import (
    Invitation,
    InvitationStatus,
    default_expiry,
)
from apps.invitations.serializers import InvitationSerializer
from apps.notifications.models import NotificationType
from apps.notifications.services import create_notification
from apps.workspaces.models import WorkspaceMember, WorkspaceRole

User = get_user_model()


@extend_schema(tags=["invitations"])
class InvitationViewSet(viewsets.ModelViewSet):
    """Invite people to a workspace and manage the invite lifecycle.

    Admins create/cancel/resend; the invited user accepts/rejects by token.
    Invitations are keyed by their (unguessable) token in the URL.
    """

    serializer_class = InvitationSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "token"
    lookup_value_regex = "[^/]+"
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Invitation.objects.none()

        user = self.request.user
        params = self.request.query_params

        # Invitations addressed to me, or for workspaces I administer.
        qs = Invitation.objects.filter(
            Q(email__iexact=user.email)
            | Q(
                workspace__members__user=user,
                workspace__members__role__in=(WorkspaceRole.OWNER, WorkspaceRole.ADMIN),
            )
        ).select_related("workspace", "invited_by").distinct()

        if params.get("mine") == "true":
            qs = qs.filter(email__iexact=user.email)
        if params.get("workspace"):
            qs = qs.filter(workspace_id=params["workspace"])
        if params.get("status"):
            qs = qs.filter(status=params["status"])
        return qs

    # ------------------------------------------------------------------ helpers
    def _is_admin(self, workspace) -> bool:
        member = workspace.members.filter(user=self.request.user).first()
        return member is not None and member.role in (
            WorkspaceRole.OWNER,
            WorkspaceRole.ADMIN,
        )

    def _require_recipient(self, invitation):
        if invitation.email.lower() != self.request.user.email.lower():
            raise PermissionDenied("This invitation was sent to a different email.")

    def _notify(self, invitation):
        recipient = User.objects.filter(email__iexact=invitation.email).first()
        if not recipient:
            return
        inviter = invitation.invited_by
        create_notification(
            recipient=recipient,
            actor=inviter,
            workspace=invitation.workspace,
            type=NotificationType.WORKSPACE_INVITE,
            title=f"{inviter.name or inviter.email} invited you to {invitation.workspace.name}",
            link="/invitations",
        )

    # -------------------------------------------------------------------- create
    def perform_create(self, serializer):
        workspace = serializer.validated_data["workspace"]
        if not self._is_admin(workspace):
            raise PermissionDenied("Only workspace admins can invite members.")
        invitation = serializer.save(invited_by=self.request.user)
        self._notify(invitation)
        log_activity(
            actor=self.request.user,
            workspace=workspace,
            action="member.invited",
            metadata={"email": invitation.email, "role": invitation.role},
        )

    # ------------------------------------------------------------------- destroy
    def destroy(self, request, *args, **kwargs):
        invitation = self.get_object()
        if not self._is_admin(invitation.workspace):
            raise PermissionDenied("Only workspace admins can cancel invitations.")
        invitation.status = InvitationStatus.CANCELLED
        invitation.save(update_fields=["status", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ------------------------------------------------------------------- actions
    @action(detail=True, methods=["post"])
    def resend(self, request, token=None):
        invitation = self.get_object()
        if not self._is_admin(invitation.workspace):
            raise PermissionDenied("Only workspace admins can resend invitations.")
        if invitation.status not in (InvitationStatus.PENDING, InvitationStatus.EXPIRED):
            raise ValidationError("Only pending or expired invitations can be resent.")
        invitation.status = InvitationStatus.PENDING
        invitation.expires_at = default_expiry()
        invitation.save(update_fields=["status", "expires_at", "updated_at"])
        self._notify(invitation)
        return Response(self.get_serializer(invitation).data)

    @action(detail=True, methods=["post"])
    def accept(self, request, token=None):
        invitation = self.get_object()
        self._require_recipient(invitation)
        if invitation.status != InvitationStatus.PENDING:
            raise ValidationError("This invitation is no longer pending.")
        if invitation.is_expired:
            invitation.status = InvitationStatus.EXPIRED
            invitation.save(update_fields=["status", "updated_at"])
            raise ValidationError("This invitation has expired.")

        WorkspaceMember.objects.get_or_create(
            workspace=invitation.workspace,
            user=request.user,
            defaults={"role": invitation.role},
        )
        invitation.status = InvitationStatus.ACCEPTED
        invitation.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(invitation).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, token=None):
        invitation = self.get_object()
        self._require_recipient(invitation)
        if invitation.status != InvitationStatus.PENDING:
            raise ValidationError("This invitation is no longer pending.")
        invitation.status = InvitationStatus.REJECTED
        invitation.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(invitation).data)
