"""Notification creation helpers + small link builder."""

from django.db import transaction

from apps.notifications.models import Notification

# Maps a content-type model name to its frontend route prefix.
_TARGET_PATHS = {
    "project": "/projects/",
    "task": "/tasks/",
    "document": "/documents/",
    "handover": "/handovers/",
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

    notification = Notification.objects.create(
        recipient=recipient,
        actor=actor,
        workspace=workspace,
        type=type,
        title=title,
        message=message,
        link=link,
    )
    _push(notification)
    return notification


def _push(notification) -> None:
    """Deliver ``notification`` over the recipient's websocket, if any.

    Deferred until after commit: pushing inside the transaction can beat the
    write to the database, and a client that then refetches would not yet see
    the row. On a rollback nothing is sent at all, which is the point.
    """
    # Imported here to keep this module importable without Channels loaded.
    from apps.notifications.consumers import push_to_user
    from apps.notifications.serializers import NotificationSerializer

    recipient_id = notification.recipient_id
    unread = Notification.objects.filter(
        recipient_id=recipient_id, is_read=False
    ).count()
    payload = NotificationSerializer(notification).data

    def deliver():
        push_to_user(
            recipient_id, {"type": "notification.created", "data": payload}
        )
        push_to_user(recipient_id, {"type": "unread.count", "count": unread})

    transaction.on_commit(deliver)
