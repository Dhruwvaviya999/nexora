"""Activity logging helper."""

from django.contrib.contenttypes.models import ContentType

from apps.activities.models import Activity


def log_activity(*, actor, workspace, action, target=None, metadata=None):
    """Append an activity row. ``target`` is optional (None for deletes)."""
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
