"""
Workspace invitation.

An emailed invite carrying an unguessable token. The recipient accepts/rejects
with the token; workspace admins can cancel or resend. Accepting creates the
``WorkspaceMember`` (which the activity log picks up automatically).
"""

import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.models import BaseModel
from apps.workspaces.models import WorkspaceRole


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def default_expiry():
    return timezone.now() + timedelta(days=7)


class InvitationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    ACCEPTED = "accepted", "Accepted"
    REJECTED = "rejected", "Rejected"
    EXPIRED = "expired", "Expired"
    CANCELLED = "cancelled", "Cancelled"


# Owner is never an invitable role — ownership transfers are a separate flow.
INVITABLE_ROLES = (WorkspaceRole.ADMIN, WorkspaceRole.MEMBER)


class Invitation(BaseModel):
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="invitations",
    )
    email = models.EmailField()
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_invitations",
    )
    role = models.CharField(
        max_length=20, choices=WorkspaceRole.choices, default=WorkspaceRole.MEMBER
    )
    status = models.CharField(
        max_length=20,
        choices=InvitationStatus.choices,
        default=InvitationStatus.PENDING,
    )
    token = models.CharField(max_length=64, unique=True, default=generate_token)
    expires_at = models.DateTimeField(default=default_expiry)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["workspace", "status"])]

    def __str__(self) -> str:
        return f"{self.email} -> {self.workspace} ({self.status})"

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at
