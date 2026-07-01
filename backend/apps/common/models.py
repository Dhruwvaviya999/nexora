"""
Reusable abstract base models.

These carry no database tables of their own (``abstract = True``); future apps
inherit from them to get consistent UUID primary keys and timestamp columns
without repeating boilerplate.
"""

import uuid

from django.conf import settings
from django.db import models


class TimeStampedModel(models.Model):
    """Adds self-managed ``created_at`` / ``updated_at`` timestamps."""

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        abstract = True
        ordering = ("-created_at",)


class UUIDModel(models.Model):
    """Uses a non-sequential UUID primary key (safe to expose in URLs/APIs)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class BaseModel(UUIDModel, TimeStampedModel):
    """Default base for domain models: UUID id + timestamps."""

    class Meta:
        abstract = True
        ordering = ("-created_at",)


class AuditModel(BaseModel):
    """BaseModel + who-created / who-last-updated tracking.

    ``related_name="+"`` disables the reverse accessors so many models can
    share these FKs without clashing on the user model.
    """

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        abstract = True
        ordering = ("-created_at",)


class WorkspaceScopedModel(AuditModel):
    """Every domain object hangs off a workspace (the tenant boundary).

    Uses ``%(class)ss`` so each concrete model gets a sensible reverse name
    (``workspace.projects``, ``workspace.tasks``, ``workspace.documents``).
    """

    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="%(class)ss",
    )

    class Meta:
        abstract = True
        ordering = ("-created_at",)
