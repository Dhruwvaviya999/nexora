"""
Reusable abstract base models.

These carry no database tables of their own (``abstract = True``); future apps
inherit from them to get consistent UUID primary keys and timestamp columns
without repeating boilerplate.
"""

import uuid

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
