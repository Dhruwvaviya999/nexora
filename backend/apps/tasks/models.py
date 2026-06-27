"""Task model — a unit of work inside a project."""

from django.conf import settings
from django.db import models

from apps.common.models import WorkspaceScopedModel


class TaskStatus(models.TextChoices):
    TODO = "todo", "Todo"
    IN_PROGRESS = "in_progress", "In progress"
    REVIEW = "review", "Review"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"


class TaskPriority(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    CRITICAL = "critical", "Critical"


class Task(WorkspaceScopedModel):
    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="tasks"
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20, choices=TaskStatus.choices, default=TaskStatus.TODO
    )
    priority = models.CharField(
        max_length=20, choices=TaskPriority.choices, default=TaskPriority.MEDIUM
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tasks",
    )
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reported_tasks",
    )
    due_date = models.DateField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    estimated_hours = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    # Simple list of string labels, e.g. ["bug", "frontend"].
    labels = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["workspace", "status"]),
            models.Index(fields=["project", "status"]),
        ]

    def __str__(self) -> str:
        return self.title
