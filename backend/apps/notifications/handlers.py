"""
Signal receivers that turn domain events into notifications.

This is the only place that knows "a mention/reply should notify someone", so
the mentions and comments apps stay unaware of notifications.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.comments.models import Comment
from apps.mentions.signals import user_mentioned
from apps.notifications.models import NotificationType
from apps.notifications.services import create_notification, link_for


def _display(user) -> str:
    return user.name or user.email


@receiver(user_mentioned, dispatch_uid="notifications_on_mention")
def on_user_mentioned(sender, mention, comment, actor, recipient, **kwargs):
    create_notification(
        recipient=recipient,
        actor=actor,
        workspace=comment.workspace,
        type=NotificationType.MENTION,
        title=f"{_display(actor)} mentioned you",
        message=(comment.content or "")[:140],
        link=link_for(comment.content_type, comment.object_id),
    )


@receiver(post_save, sender=Comment, dispatch_uid="notifications_on_reply")
def on_comment_reply(sender, instance, created, **kwargs):
    if not created or instance.is_deleted or not instance.parent_id:
        return
    create_notification(
        recipient=instance.parent.author,
        actor=instance.author,
        workspace=instance.workspace,
        type=NotificationType.COMMENT_REPLY,
        title=f"{_display(instance.author)} replied to your comment",
        message=(instance.content or "")[:140],
        link=link_for(instance.content_type, instance.object_id),
    )
