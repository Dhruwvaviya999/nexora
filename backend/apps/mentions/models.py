"""
Mention model.

Records that a user was @-mentioned inside a comment. One row per
(comment, mentioned_user). The notifications app (later) turns these into
user-facing notifications by listening to the ``user_mentioned`` signal.
"""

from django.conf import settings
from django.db import models

from apps.common.models import BaseModel


class Mention(BaseModel):
    comment = models.ForeignKey(
        "comments.Comment",
        on_delete=models.CASCADE,
        related_name="mentions",
    )
    mentioned_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mentions_received",
    )
    # Denormalised from the comment for cheap "my mentions in workspace X" reads.
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="mentions",
    )

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("comment", "mentioned_user"),
                name="unique_comment_mention",
            )
        ]

    def __str__(self) -> str:
        return f"{self.mentioned_user} mentioned in {self.comment_id}"
