"""
Reusable DRF permission classes.

These are workspace-aware and designed to be shared by every future module
(projects, tasks, documents, …). They resolve the relevant workspace from the
object under check:

* if the object *is* a ``Workspace``  -> use it directly
* otherwise                           -> use ``obj.workspace``

so a single permission class protects both a workspace and anything nested
inside it.
"""

from rest_framework.permissions import BasePermission, SAFE_METHODS


def _resolve_workspace(obj):
    """Return the Workspace associated with ``obj`` (or ``obj`` itself)."""
    # Local import avoids a circular dependency (workspaces -> common).
    from apps.workspaces.models import Workspace

    if isinstance(obj, Workspace):
        return obj
    return getattr(obj, "workspace", None)


def _membership(user, workspace):
    if workspace is None or not user or not user.is_authenticated:
        return None
    return workspace.members.filter(user=user).first()


class IsWorkspaceMember(BasePermission):
    """Allow any member of the workspace."""

    message = "You must be a member of this workspace."

    def has_object_permission(self, request, view, obj):
        return _membership(request.user, _resolve_workspace(obj)) is not None


class IsWorkspaceAdmin(BasePermission):
    """Allow workspace owners and admins."""

    message = "You must be a workspace admin."

    def has_object_permission(self, request, view, obj):
        from apps.workspaces.models import WorkspaceRole

        member = _membership(request.user, _resolve_workspace(obj))
        return member is not None and member.role in (
            WorkspaceRole.OWNER,
            WorkspaceRole.ADMIN,
        )


class IsWorkspaceOwner(BasePermission):
    """Allow only the workspace owner."""

    message = "Only the workspace owner can perform this action."

    def has_object_permission(self, request, view, obj):
        from apps.workspaces.models import WorkspaceRole

        member = _membership(request.user, _resolve_workspace(obj))
        return member is not None and member.role == WorkspaceRole.OWNER


class IsWorkspaceAdminOrReadOnly(BasePermission):
    """Members may read; only owners/admins may write."""

    message = "You must be a workspace admin to modify this."

    def has_object_permission(self, request, view, obj):
        from apps.workspaces.models import WorkspaceRole

        member = _membership(request.user, _resolve_workspace(obj))
        if member is None:
            return False
        if request.method in SAFE_METHODS:
            return True
        return member.role in (WorkspaceRole.OWNER, WorkspaceRole.ADMIN)
