"""Notification creation helpers + small link builder."""

from apps.notifications.models import Notification

# Maps a content-type model name to its frontend route prefix.
_TARGET_PATHS = {
    "project": "/projects/",
    "task": "/tasks/",
    "document": "/documents/",
}


def link_for(content_type, object_id) -> str:
    """Build the frontend link for a commented-on object, e.g. /tasks/<id>."""
    prefix = _TARGET_PATHS.get(content_type.model, "/")
    return f"{prefix}{object_id}"


def create_notification(
    *,
    recipient,
    type,
    title,
    actor=None,
    workspace=None,
    message="",
    link="",
):
    """Create a notification, skipping self-notifications.

    Returns the Notification, or None when it was skipped (recipient is the
    actor, or there is no recipient).
    """
    if recipient is None:
        return None
    if actor is not None and recipient.pk == actor.pk:
        return None

    return Notification.objects.create(
        recipient=recipient,
        actor=actor,
        workspace=workspace,
        type=type,
        title=title,
        message=message,
        link=link,
    )
