"""
Custom user model.

Defined at project start (the recommended Django practice) so the user table
can be extended in later phases without a disruptive migration. Phase 1 keeps
it intentionally minimal — no authentication logic lives here yet. It swaps the
primary key for a UUID and makes ``email`` a required, unique field, which is
what later auth flows will key off.
"""

import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField("email address", unique=True)

    class Meta:
        db_table = "accounts_user"
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self) -> str:
        return self.get_username()
