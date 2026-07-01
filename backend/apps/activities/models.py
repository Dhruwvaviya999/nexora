"""
Activity log.

An append-only audit trail. Rows are written by signal handlers (never by hand
at call sites) so adding history to a new model is just one line of wiring.
``action`` is a dotted string like ``task.created`` / ``project.archived``;
``metadata`` carries a small human-readable snapshot (name, status, …).
"""

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from apps.common.models import BaseModel


class Activity(BaseModel):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="activities",
    )

    action = models.CharField(max_length=64)

    # Optional pointer to the affected object (null for deletes).
    content_type = models.ForeignKey(
        ContentType, on_delete=models.SET_NULL, null=True, blank=True
    )
    object_id = models.UUIDField(null=True, blank=True)
    target = GenericForeignKey("content_type", "object_id")

    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name_plural = "activities"
        indexes = [
            models.Index(fields=["workspace", "created_at"]),
            models.Index(fields=["content_type", "object_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.action} by {self.actor}"
