"""Activity logging helper."""

from django.contrib.contenttypes.models import ContentType

from apps.activities.models import Activity

# Workspaces currently being deleted, by primary key.
#
# Deleting a workspace cascades into every child object, and each cascade fires
# the post_delete handlers in apps.activities.handlers. Those would append
# activity rows referencing a workspace that is about to be removed, which the
# database rejects as a foreign key violation when the transaction commits —
# taking the whole delete down with it. The rows would be pointless anyway:
# Activity.workspace cascades, so they die with the workspace.
_workspaces_being_deleted: set[str] = set()


def suppress_activity_for_workspace(pk) -> None:
    """Stop recording activity for a workspace that is being deleted."""
    _workspaces_being_deleted.add(str(pk))


def resume_activity_for_workspace(pk) -> None:
    """Undo :func:`suppress_activity_for_workspace` once the delete is done."""
    _workspaces_being_deleted.discard(str(pk))


def log_activity(*, actor, workspace, action, target=None, metadata=None):
    """Append an activity row. ``target`` is optional (None for deletes)."""
    workspace_pk = getattr(workspace, "pk", workspace)
    if workspace_pk is not None and str(workspace_pk) in _workspaces_being_deleted:
        return None

    content_type = None
    object_id = None
    if target is not None:
        content_type = ContentType.objects.get_for_model(target.__class__)
        object_id = target.pk

    return Activity.objects.create(
        actor=actor,
        workspace=workspace,
        action=action,
        content_type=content_type,
        object_id=object_id,
        metadata=metadata or {},
    )
