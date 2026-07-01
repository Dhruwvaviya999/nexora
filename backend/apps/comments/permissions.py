"""Object-level permission for editing/deleting comments."""

from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.workspaces.models import WorkspaceRole


class IsAuthorOrWorkspaceAdmin(BasePermission):
    """Reads are open to members (already scoped by the queryset).

    Editing is author-only; deleting is allowed for the author or for a
    workspace owner/admin (moderation).
    """

    message = "You can only modify your own comments."

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        if obj.author_id == request.user.id:
            return True

        if request.method == "DELETE":
            member = obj.workspace.members.filter(user=request.user).first()
            return member is not None and member.role in (
                WorkspaceRole.OWNER,
                WorkspaceRole.ADMIN,
            )

        return False
