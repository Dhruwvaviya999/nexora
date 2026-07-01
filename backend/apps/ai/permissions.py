"""
AI-app permission helpers.

The action endpoints (chat/search/summarize/...) receive the workspace id in the
request body rather than the URL, so they can't rely on DRF object-permissions
alone. ``resolve_workspace`` centralises "is this user allowed to act in this
workspace" and returns the Workspace, raising the right DRF error otherwise.
"""

from __future__ import annotations

from rest_framework.exceptions import NotFound, PermissionDenied


def resolve_workspace(user, workspace_id, *, require_admin: bool = False):
    """Return the workspace if ``user`` is a member (optionally an admin)."""
    from apps.workspaces.models import Workspace, WorkspaceRole

    workspace = Workspace.objects.filter(pk=workspace_id).first()
    if workspace is None:
        raise NotFound("Workspace not found.")

    member = workspace.members.filter(user=user).first()
    if member is None:
        raise PermissionDenied("You are not a member of this workspace.")

    if require_admin and member.role not in (
        WorkspaceRole.OWNER,
        WorkspaceRole.ADMIN,
    ):
        raise PermissionDenied("You must be a workspace admin.")

    return workspace
