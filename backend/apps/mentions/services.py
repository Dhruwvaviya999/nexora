"""
Mention parsing + sync.

Mentions are stored in comment text as tokens the frontend autocomplete emits:

    @[Display Name](<user-uuid>)

This is unambiguous and needs no separate username field on the user model.
``sync_comment_mentions`` is idempotent: it adds mentions that appear, drops
ones removed by an edit, and only fires the signal for genuinely new mentions.
"""

import re

from django.contrib.auth import get_user_model

from apps.mentions.models import Mention
from apps.mentions.signals import user_mentioned

User = get_user_model()

# @[anything](uuid)
_MENTION_RE = re.compile(r"@\[[^\]]+\]\(([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})\)")


def extract_mentioned_ids(text: str) -> set[str]:
    """Return the set of user UUIDs referenced in ``text``."""
    return set(_MENTION_RE.findall(text or ""))


def sync_comment_mentions(comment) -> None:
    """Reconcile Mention rows for a comment against its current content."""
    ids = extract_mentioned_ids(comment.content)

    # Only users who are members of the comment's workspace can be mentioned,
    # and never the author themselves.
    valid_users = (
        User.objects.filter(
            id__in=ids,
            workspace_memberships__workspace=comment.workspace,
        )
        .exclude(id=comment.author_id)
        .distinct()
    )
    valid_ids = {user.id for user in valid_users}

    existing = {m.mentioned_user_id: m for m in comment.mentions.all()}

    # Add new mentions and notify.
    for user in valid_users:
        if user.id in existing:
            continue
        mention = Mention.objects.create(
            comment=comment,
            mentioned_user=user,
            workspace=comment.workspace,
        )
        user_mentioned.send(
            sender=Mention,
            mention=mention,
            comment=comment,
            actor=comment.author,
            recipient=user,
        )

    # Drop mentions removed by an edit.
    for user_id, mention in existing.items():
        if user_id not in valid_ids:
            mention.delete()
