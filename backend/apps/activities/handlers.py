"""
Signal wiring that records activity.

Domain apps stay untouched — adding history is just registering a model here.
Connections use ``weak=False`` because the handler closures aren't referenced
anywhere else and would otherwise be garbage-collected.
"""

from django.db.models.signals import post_delete, post_save

from apps.activities.services import log_activity
from apps.comments.models import Comment
from apps.documents.models import Document
from apps.projects.models import Project
from apps.tasks.models import Task
from apps.workspaces.models import Workspace, WorkspaceMember


def _audit_actor(instance, created):
    """Actor for AuditModel-based instances (project/task/document)."""
    return instance.created_by if created else instance.updated_by


def _register_audited(model, entity, label):
    """Wire create/update/delete logging for a workspace-scoped audited model."""

    def on_save(sender, instance, created, **kwargs):
        log_activity(
            actor=_audit_actor(instance, created),
            workspace=instance.workspace,
            action=f"{entity}.{'created' if created else 'updated'}",
            target=instance,
            metadata=label(instance),
        )

    def on_delete(sender, instance, **kwargs):
        log_activity(
            actor=instance.updated_by or instance.created_by,
            workspace=instance.workspace,
            action=f"{entity}.deleted",
            metadata=label(instance),
        )

    post_save.connect(on_save, sender=model, weak=False, dispatch_uid=f"activity_save_{entity}")
    post_delete.connect(on_delete, sender=model, weak=False, dispatch_uid=f"activity_delete_{entity}")


_register_audited(Project, "project", lambda i: {"name": i.name, "archived": i.archived})
_register_audited(Task, "task", lambda i: {"title": i.title, "status": i.status})
_register_audited(Document, "document", lambda i: {"title": i.title})


def _on_comment_created(sender, instance, created, **kwargs):
    if not created or instance.is_deleted:
        return
    log_activity(
        actor=instance.author,
        workspace=instance.workspace,
        action="comment.created",
        target=instance,
        metadata={"excerpt": (instance.content or "")[:80]},
    )


def _on_workspace_save(sender, instance, created, **kwargs):
    log_activity(
        actor=instance.owner,
        workspace=instance,
        action=f"workspace.{'created' if created else 'updated'}",
        target=instance,
        metadata={"name": instance.name},
    )


def _on_member_joined(sender, instance, created, **kwargs):
    if not created:
        return
    log_activity(
        actor=instance.user,
        workspace=instance.workspace,
        action="member.joined",
        metadata={"user": instance.user.email, "role": instance.role},
    )


def _on_member_removed(sender, instance, **kwargs):
    log_activity(
        actor=None,
        workspace=instance.workspace,
        action="member.removed",
        metadata={"user": instance.user.email},
    )


post_save.connect(_on_comment_created, sender=Comment, weak=False, dispatch_uid="activity_comment_created")
post_save.connect(_on_workspace_save, sender=Workspace, weak=False, dispatch_uid="activity_workspace_save")
post_save.connect(_on_member_joined, sender=WorkspaceMember, weak=False, dispatch_uid="activity_member_joined")
post_delete.connect(_on_member_removed, sender=WorkspaceMember, weak=False, dispatch_uid="activity_member_removed")
