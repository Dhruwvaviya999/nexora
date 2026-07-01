"""
AI summaries for projects, tasks, documents and workspace activity.

Gathers the target's data (strictly workspace-scoped), builds a summary prompt
and returns the LLM's markdown summary. All gather helpers assume the caller has
already verified workspace membership.
"""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from apps.ai.providers import get_llm_provider
from apps.ai.providers.factory import get_llm_settings
from apps.ai.services import prompts

VALID_TARGETS = ("project", "task", "document", "activity")


class SummaryError(Exception):
    """Raised for invalid summary requests (bad target / missing object)."""


def _gather_project(workspace, target_id: str) -> tuple[str, str]:
    from apps.projects.models import Project
    from apps.tasks.models import Task

    project = Project.objects.filter(workspace=workspace, pk=target_id).first()
    if project is None:
        raise SummaryError("Project not found in this workspace.")

    tasks = Task.objects.filter(project=project).select_related("assignee")
    lines = [
        f"Project: {project.name}",
        f"Status: {project.status}",
        f"Description: {project.description or '(none)'}",
        f"Total tasks: {tasks.count()}",
        "",
        "Tasks:",
    ]
    for t in tasks.order_by("status")[:50]:
        assignee = getattr(t.assignee, "name", None) or "unassigned"
        lines.append(f"- [{t.status}] {t.title} (assignee: {assignee})")
    return "project", "\n".join(lines)


def _gather_task(workspace, target_id: str) -> tuple[str, str]:
    from apps.tasks.models import Task

    task = (
        Task.objects.filter(workspace=workspace, pk=target_id)
        .select_related("assignee", "reporter", "project")
        .first()
    )
    if task is None:
        raise SummaryError("Task not found in this workspace.")

    content = (
        f"Title: {task.title}\n"
        f"Project: {getattr(task.project, 'name', '—')}\n"
        f"Status: {task.status}\nPriority: {task.priority}\n"
        f"Assignee: {getattr(task.assignee, 'name', None) or 'unassigned'}\n"
        f"Due: {task.due_date.isoformat() if task.due_date else 'none'}\n\n"
        f"Description:\n{task.description or '(none)'}"
    )
    return "task", content


def _gather_document(workspace, target_id: str) -> tuple[str, str]:
    from apps.documents.models import Document

    document = Document.objects.filter(workspace=workspace, pk=target_id).first()
    if document is None:
        raise SummaryError("Document not found in this workspace.")

    chunks = document.chunks.order_by("chunk_index")[:40]
    body = "\n\n".join(c.content for c in chunks)
    if not body:
        raise SummaryError(
            "This document has not been processed yet — try again shortly."
        )
    return "document", f"Title: {document.title}\n\n{body}"


def _gather_activity(workspace, period: str = "week") -> tuple[str, str]:
    from apps.activities.models import Activity

    days = {"day": 1, "week": 7, "month": 30}.get(period, 7)
    since = timezone.now() - timedelta(days=days)
    activities = (
        Activity.objects.filter(workspace=workspace, created_at__gte=since)
        .select_related("actor")
        .order_by("-created_at")[:200]
    )
    lines = [f"Workspace activity over the last {days} day(s):", ""]
    for a in activities:
        actor = getattr(a.actor, "name", None) or "system"
        lines.append(f"- {a.created_at.date()}: {actor} {a.action} {a.metadata}")
    if len(lines) == 2:
        lines.append("(no activity in this period)")
    return f"{period}ly activity report", "\n".join(lines)


def summarize(
    *,
    workspace,
    target_type: str,
    target_id: str | None = None,
    period: str = "week",
) -> dict:
    if target_type not in VALID_TARGETS:
        raise SummaryError(f"Invalid target_type: {target_type!r}")

    if target_type == "activity":
        label, content = _gather_activity(workspace, period)
    else:
        if not target_id:
            raise SummaryError("target_id is required for this summary.")
        gather = {
            "project": _gather_project,
            "task": _gather_task,
            "document": _gather_document,
        }[target_type]
        label, content = gather(workspace, target_id)

    messages = prompts.build_summary_messages(target_label=label, content=content)
    cfg = get_llm_settings(workspace)
    provider = get_llm_provider(workspace)
    response = provider.generate(
        messages, temperature=cfg["temperature"], max_tokens=cfg["max_tokens"]
    )
    return {"summary": response.text, "target_type": target_type, "model": response.model}
