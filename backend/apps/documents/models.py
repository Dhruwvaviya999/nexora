"""
Document model — a file stored against a workspace (optionally a project).

Files go through Django's storage backend (``STORAGES["default"]``). Locally
that's the filesystem; swapping to S3 or Cloudinary later is a settings change
(e.g. django-storages / cloudinary) with no model changes required.
"""

from django.conf import settings
from django.db import models

from apps.common.models import WorkspaceScopedModel


def document_upload_path(instance, filename: str) -> str:
    # Partition by workspace to keep buckets tidy and migrations storage-agnostic.
    return f"documents/{instance.workspace_id}/{filename}"


class Document(WorkspaceScopedModel):
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    file = models.FileField(upload_to=document_upload_path)
    # Denormalised metadata, populated on upload.
    file_type = models.CharField(max_length=100, blank=True, default="")
    file_size = models.PositiveBigIntegerField(default=0)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_documents",
    )

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return self.title
