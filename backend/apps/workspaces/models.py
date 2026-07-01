"""
Workspace domain models.

A ``Workspace`` is the top-level tenant boundary: every future feature
(projects, tasks, documents, …) will hang off a workspace. ``WorkspaceMember``
joins users to workspaces with a role, which the permission classes in
``apps.common.permissions`` read.
"""

from django.conf import settings
from django.db import models
from django.utils.text import slugify

from apps.common.models import BaseModel


class WorkspaceRole(models.TextChoices):
    OWNER = "owner", "Owner"
    ADMIN = "admin", "Admin"
    MEMBER = "member", "Member"


class Workspace(BaseModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.TextField(blank=True, default="")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_workspaces",
    )

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._generate_unique_slug()
        super().save(*args, **kwargs)

    def _generate_unique_slug(self) -> str:
        base = slugify(self.name) or "workspace"
        slug = base
        counter = 2
        while Workspace.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base}-{counter}"
            counter += 1
        return slug


class WorkspaceMember(BaseModel):
    workspace = models.ForeignKey(
        Workspace, on_delete=models.CASCADE, related_name="members"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="workspace_memberships",
    )
    role = models.CharField(
        max_length=20, choices=WorkspaceRole.choices, default=WorkspaceRole.MEMBER
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("joined_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("workspace", "user"), name="unique_workspace_member"
            )
        ]

    def __str__(self) -> str:
        return f"{self.user} @ {self.workspace} ({self.role})"
