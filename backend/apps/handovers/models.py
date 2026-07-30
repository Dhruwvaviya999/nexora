"""Handover model — a formal transfer of a task from one member to another.

The outgoing member submits a handover (work summary, pending items,
resources). A workspace manager/admin/owner then reviews it: approving
reassigns the task to the recipient; rejecting sends it back with a comment.
"""

from django.conf import settings
from django.db import models

from apps.common.models import WorkspaceScopedModel


class HandoverStatus(models.TextChoices):
    PENDING = "pending", "Pending review"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class Handover(WorkspaceScopedModel):
    task = models.ForeignKey(
        "tasks.Task", on_delete=models.CASCADE, related_name="handovers"
    )
    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="handovers_sent",
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="handovers_received",
    )

    # What the recipient needs to pick the work up.
    summary = models.TextField()
    pending_items = models.TextField(blank=True, default="")
    resources = models.TextField(blank=True, default="")

    status = models.CharField(
        max_length=20, choices=HandoverStatus.choices, default=HandoverStatus.PENDING
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="handovers_reviewed",
    )
    review_comment = models.TextField(blank=True, default="")
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["workspace", "status"]),
            models.Index(fields=["task", "status"]),
        ]

    def __str__(self) -> str:
        return f"Handover of {self.task} ({self.status})"
