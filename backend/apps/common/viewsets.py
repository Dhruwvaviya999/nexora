"""
Reusable viewset base for workspace-scoped resources.

Projects, tasks, and documents all share the same access pattern: a member of a
workspace may operate on objects inside it. This base centralises that logic so
each module only declares its serializer, filterset, and search/ordering fields.
"""

from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from apps.common.permissions import IsWorkspaceMember


class WorkspaceScopedViewSet(ModelViewSet):
    """ModelViewSet scoped to the workspaces the requesting user belongs to.

    Subclasses must set ``queryset`` (used only for its model/relations) plus the
    usual ``serializer_class`` / ``filterset_class`` / ``search_fields`` /
    ``ordering_fields``.
    """

    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def get_queryset(self):
        # No authenticated user during schema generation.
        if getattr(self, "swagger_fake_view", False):
            return self.queryset.model.objects.none()
        return (
            self.queryset.filter(workspace__members__user=self.request.user)
            .distinct()
        )

    def _require_membership(self, workspace):
        if workspace is None:
            raise ValidationError({"workspace": "This field is required."})
        if not workspace.members.filter(user=self.request.user).exists():
            raise PermissionDenied("You are not a member of this workspace.")

    def perform_create(self, serializer):
        self._require_membership(serializer.validated_data.get("workspace"))
        serializer.save(
            created_by=self.request.user, updated_by=self.request.user
        )

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)
