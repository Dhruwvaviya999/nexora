"""Signal wiring: keep mentions in sync whenever a comment is saved."""

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.comments.models import Comment
from apps.mentions.services import sync_comment_mentions


@receiver(post_save, sender=Comment, dispatch_uid="mentions_sync_on_comment_save")
def sync_mentions_on_comment_save(sender, instance, **kwargs):
    # A soft-deleted comment has empty content, so this also clears its mentions.
    sync_comment_mentions(instance)
