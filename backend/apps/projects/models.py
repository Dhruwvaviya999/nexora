"""Project model — a container for tasks and documents inside a workspace."""

from django.conf import settings
from django.db import models
from django.utils.text import slugify

from apps.common.models import WorkspaceScopedModel


class ProjectStatus(models.TextChoices):
    PLANNING = "planning", "Planning"
    ACTIVE = "active", "Active"
    ON_HOLD = "on_hold", "On hold"
    COMPLETED = "completed", "Completed"


class Project(WorkspaceScopedModel):
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=170, blank=True)
    description = models.TextField(blank=True, default="")
    # Hex colour used for UI accents (e.g. #6366f1).
    color = models.CharField(max_length=7, blank=True, default="#6366f1")
    status = models.CharField(
        max_length=20, choices=ProjectStatus.choices, default=ProjectStatus.PLANNING
    )
    archived = models.BooleanField(default=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_projects",
    )

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("workspace", "slug"), name="unique_project_slug_per_workspace"
            )
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._generate_unique_slug()
        super().save(*args, **kwargs)

    def _generate_unique_slug(self) -> str:
        base = slugify(self.name) or "project"
        slug = base
        counter = 2
        siblings = Project.objects.filter(workspace=self.workspace).exclude(pk=self.pk)
        while siblings.filter(slug=slug).exists():
            slug = f"{base}-{counter}"
            counter += 1
        return slug
