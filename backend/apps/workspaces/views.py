"""Workspace API views."""

from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
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
