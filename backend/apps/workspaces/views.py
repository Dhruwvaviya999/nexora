"""Workspace API views."""

from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.permissions import (
    IsWorkspaceAdminOrReadOnly,
    IsWorkspaceMember,
    IsWorkspaceOwner,
)
from apps.workspaces.models import Workspace, WorkspaceMember, WorkspaceRole
from apps.workspaces.serializers import (
    WorkspaceMemberSerializer,
    WorkspaceSerializer,
)


@extend_schema(tags=["workspaces"])
class WorkspaceViewSet(viewsets.ModelViewSet):
    """CRUD for workspaces the current user belongs to.

    Permission matrix (object level):
      * list / retrieve  -> any member
      * create           -> any authenticated user
      * update / partial -> owner or admin
      * destroy          -> owner only
    """

    serializer_class = WorkspaceSerializer
    lookup_field = "pk"

    def get_queryset(self):
        # During OpenAPI schema generation there is no authenticated user.
        if getattr(self, "swagger_fake_view", False):
            return Workspace.objects.none()
        # Only workspaces the user is a member of, with related data prefetched.
        return (
            Workspace.objects.filter(members__user=self.request.user)
            .select_related("owner")
            .prefetch_related("members")
            .distinct()
        )

    def get_permissions(self):
        if self.action in ("update", "partial_update"):
            perms = [IsAuthenticated, IsWorkspaceAdminOrReadOnly]
        elif self.action == "destroy":
            perms = [IsAuthenticated, IsWorkspaceOwner]
        elif self.action in ("retrieve", "members"):
            perms = [IsAuthenticated, IsWorkspaceMember]
        else:  # list, create
            perms = [IsAuthenticated]
        return [perm() for perm in perms]

    @transaction.atomic
    def perform_create(self, serializer):
        workspace = serializer.save(owner=self.request.user)
        # The creator is automatically the owner member.
        WorkspaceMember.objects.create(
            workspace=workspace,
            user=self.request.user,
            role=WorkspaceRole.OWNER,
        )

    @extend_schema(responses=WorkspaceMemberSerializer(many=True))
    @action(detail=True, methods=["get"])
    def members(self, request, pk=None):
        """GET /workspaces/{id}/members/ — list workspace members."""
        workspace = self.get_object()
        members = workspace.members.select_related("user").all()
        serializer = WorkspaceMemberSerializer(members, many=True)
        return Response(serializer.data)

    def _membership(self, workspace, user):
        return workspace.members.filter(user=user).first()

    @extend_schema(
        request={"application/json": {"type": "object", "properties": {"role": {"type": "string"}}}},
        responses=WorkspaceMemberSerializer,
    )
    @action(
        detail=True,
        methods=["patch", "delete"],
        url_path=r"members/(?P<member_id>[0-9a-fA-F-]+)",
    )
    def manage_member(self, request, pk=None, member_id=None):
        """PATCH/DELETE /workspaces/{id}/members/{member_id}/ — change role or remove.

        Owners and admins only. The owner's own membership is managed through
        transfer-ownership, not here.
        """
        workspace = self.get_object()
        actor = self._membership(workspace, request.user)
        if actor is None or actor.role not in (WorkspaceRole.OWNER, WorkspaceRole.ADMIN):
            raise PermissionDenied("Only workspace owners and admins can manage members.")

        member = get_object_or_404(WorkspaceMember, pk=member_id, workspace=workspace)
        if member.role == WorkspaceRole.OWNER:
            raise ValidationError(
                "The owner's membership can't be changed here — use transfer-ownership."
            )

        if request.method == "DELETE":
            member.delete()  # member.removed activity is logged via signal
            return Response(status=status.HTTP_204_NO_CONTENT)

        new_role = request.data.get("role")
        if new_role not in (WorkspaceRole.ADMIN, WorkspaceRole.MEMBER):
            raise ValidationError({"role": "Role must be 'admin' or 'member'."})
        member.role = new_role
        member.save(update_fields=["role", "updated_at"])
        return Response(WorkspaceMemberSerializer(member).data)

    @extend_schema(
        request={"application/json": {"type": "object", "properties": {"user_id": {"type": "string"}}}},
        responses=WorkspaceSerializer,
    )
    @action(detail=True, methods=["post"], url_path="transfer-ownership")
    def transfer_ownership(self, request, pk=None):
        """POST /workspaces/{id}/transfer-ownership/ — hand ownership to another member.

        Current owner only. The old owner is demoted to admin.
        """
        workspace = self.get_object()
        actor = self._membership(workspace, request.user)
        if actor is None or actor.role != WorkspaceRole.OWNER:
            raise PermissionDenied("Only the current owner can transfer ownership.")

        user_id = request.data.get("user_id")
        if not user_id:
            raise ValidationError({"user_id": "user_id is required."})

        target = workspace.members.filter(user_id=user_id).first()
        if target is None:
            raise ValidationError({"user_id": "That user is not a member of this workspace."})
        if target.user_id == request.user.id:
            raise ValidationError("You already own this workspace.")

        with transaction.atomic():
            target.role = WorkspaceRole.OWNER
            target.save(update_fields=["role", "updated_at"])
            actor.role = WorkspaceRole.ADMIN
            actor.save(update_fields=["role", "updated_at"])
            workspace.owner_id = target.user_id
            workspace.save(update_fields=["owner", "updated_at"])

        return Response(
            WorkspaceSerializer(workspace, context={"request": request}).data
        )
