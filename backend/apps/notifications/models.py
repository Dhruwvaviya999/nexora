"""
In-app notification model.

Notifications are produced by other apps (mentions, comments, invitations, …)
through ``apps.notifications.services.create_notification`` — never built by
hand at the call site. Email delivery is intentionally out of scope for now.
"""

from django.conf import settings
from django.db import models

from apps.common.models import BaseModel


class NotificationType(models.TextChoices):
    MENTION = "mention", "Mention"
    TASK_ASSIGNED = "task_assigned", "Task assigned"
    TASK_UPDATED = "task_updated", "Task updated"
    COMMENT_REPLY = "comment_reply", "Comment reply"
    WORKSPACE_INVITE = "workspace_invite", "Workspace invite"
    SYSTEM = "system", "System"


class Notification(BaseModel):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    # The user who triggered it (null for system notifications).
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
        null=True,
        blank=True,
        related_name="notifications",
    )

    type = models.CharField(max_length=32, choices=NotificationType.choices)
    title = models.CharField(max_length=255)
    message = models.TextField(blank=True, default="")
    # Frontend route to open when the notification is clicked.
    link = models.CharField(max_length=255, blank=True, default="")

    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["recipient", "is_read"]),
        ]

    def __str__(self) -> str:
        return f"{self.type} -> {self.recipient}"
