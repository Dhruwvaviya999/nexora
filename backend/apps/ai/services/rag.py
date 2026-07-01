"""
RAG orchestration — the heart of the assistant.

    embed query -> retrieve document chunks (workspace-scoped)
                -> gather structured context (projects/tasks, workspace-scoped)
                -> build a guarded prompt -> call the workspace's LLM
                -> return {answer, sources, confidence}

Every query in here is filtered by ``workspace`` so the assistant can never read
or leak another tenant's data.
"""

from __future__ import annotations

from django.conf import settings
from django.utils import timezone

from apps.ai.providers import get_llm_provider
from apps.ai.providers.factory import get_llm_settings
from apps.ai.services import prompts, security
from apps.knowledge.services.search import semantic_search

# Stop-words removed before keyword-matching structured records.
_STOPWORDS = {
    "the", "a", "an", "is", "are", "what", "who", "which", "and", "or", "to",
    "of", "in", "on", "for", "this", "that", "our", "my", "me", "show", "list",
    "all", "with", "how", "do", "does", "i", "we", "us", "about", "tell",
}


def _keywords(query: str) -> list[str]:
    return [
        w for w in security.sanitize_input(query).lower().split()
        if len(w) > 2 and w not in _STOPWORDS
    ][:8]


def build_structured_context(workspace, query: str) -> str:
    """A compact, workspace-scoped snapshot of projects & relevant tasks."""
    from apps.projects.models import Project
    from apps.tasks.models import Task

    lines: list[str] = []
    today = timezone.localdate()
    closed_statuses = ("completed", "cancelled")

    projects = list(
        Project.objects.filter(workspace=workspace).order_by("-updated_at")[:8]
    )
    if projects:
        lines.append("PROJECTS:")
        for p in projects:
            lines.append(f"- {p.name} (status: {p.status})")

    open_tasks = Task.objects.filter(workspace=workspace).exclude(
        status__in=closed_statuses
    )
    overdue = open_tasks.filter(due_date__lt=today).count()
    lines.append(
        f"\nTASK SUMMARY: {open_tasks.count()} open, {overdue} overdue."
    )

    terms = _keywords(query)
    task_qs = Task.objects.filter(workspace=workspace).select_related(
        "assignee", "project"
    )
    if terms:
        from django.db.models import Q

        q = Q()
        for t in terms:
            q |= Q(title__icontains=t) | Q(project__name__icontains=t)
        task_qs = task_qs.filter(q)
    tasks = list(task_qs.order_by("due_date")[:10])
    if tasks:
        lines.append("\nRELEVANT TASKS:")
        for t in tasks:
            assignee = getattr(t.assignee, "name", None) or "unassigned"
            due = t.due_date.isoformat() if t.due_date else "no due date"
            project = getattr(t.project, "name", "—")
            lines.append(
                f"- {t.title} [project: {project}, status: {t.status}, "
                f"assignee: {assignee}, due: {due}]"
            )

    return "\n".join(lines)


def _confidence(top_score: float, has_structured: bool) -> str:
    if top_score >= 0.6:
        return "high"
    if top_score >= 0.4 or has_structured:
        return "medium"
    return "low"


def retrieve(workspace, query: str, *, limit: int | None = None) -> list[dict]:
    """Semantic search returning serialisable source dicts."""
    results = semantic_search(workspace=workspace, query=query, limit=limit)
    return [
        {
            "chunk_id": str(r.chunk.id),
            "document_id": str(r.chunk.document_id),
            "title": r.chunk.metadata.get("title")
            or getattr(r.chunk.document, "title", "Untitled"),
            "content": r.chunk.content,
            "chunk_index": r.chunk.chunk_index,
            "score": r.score,
        }
        for r in results
    ]


def answer_question(
    *,
    workspace,
    query: str,
    history: list[dict] | None = None,
) -> dict:
    """Full RAG turn. Returns answer text, cited sources and a confidence label."""
    query = security.sanitize_input(query)
    sources = retrieve(workspace, query)
    structured = build_structured_context(workspace, query)
    top_score = sources[0]["score"] if sources else 0.0

    messages = prompts.build_chat_messages(
        question=query,
        sources=sources,
        history=history,
        structured_context=structured,
    )

    cfg = get_llm_settings(workspace)
    provider = get_llm_provider(workspace)
    response = provider.generate(
        messages,
        temperature=cfg["temperature"],
        max_tokens=cfg["max_tokens"],
    )

    return {
        "answer": response.text,
        "sources": sources,
        "confidence": _confidence(top_score, bool(structured)),
        "top_score": top_score,
        "model": response.model,
    }
