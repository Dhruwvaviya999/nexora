"""
AI action-item generation.

Turns a document (or pasted text) into a list of suggested tasks. The tasks are
NOT persisted here — they're returned for the user to review and approve, after
which the frontend creates them through the existing Task API.
"""

from __future__ import annotations

import json
import re

from apps.ai.providers import get_llm_provider
from apps.ai.providers.factory import get_llm_settings
from apps.ai.services import prompts, security

# Must match apps.tasks.models.TaskPriority so approved suggestions are accepted
# by the existing Task create endpoint.
_VALID_PRIORITIES = {"low", "medium", "high", "critical"}
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_JSON_BLOCK = re.compile(r"\[.*\]", re.DOTALL)


class ActionItemError(Exception):
    """Raised when no content is available to extract tasks from."""


def _resolve_content(workspace, document_id: str | None, text: str | None) -> str:
    if document_id:
        from apps.documents.models import Document

        document = Document.objects.filter(
            workspace=workspace, pk=document_id
        ).first()
        if document is None:
            raise ActionItemError("Document not found in this workspace.")
        body = "\n\n".join(
            c.content for c in document.chunks.order_by("chunk_index")[:40]
        )
        if not body:
            raise ActionItemError(
                "This document has not been processed yet — try again shortly."
            )
        return body
    if text:
        return security.sanitize_input(text)
    raise ActionItemError("Provide a document or text to extract tasks from.")


def _parse(raw: str) -> list[dict]:
    """Parse the model's JSON array defensively (it may wrap it in prose)."""
    match = _JSON_BLOCK.search(raw or "")
    if not match:
        return []
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []

    cleaned = []
    for item in data:
        if not isinstance(item, dict) or not item.get("title"):
            continue
        priority = str(item.get("priority", "medium")).lower()
        if priority not in _VALID_PRIORITIES:
            priority = "medium"
        due = item.get("due_date")
        if not (isinstance(due, str) and _DATE_RE.match(due)):
            due = None
        cleaned.append(
            {
                "title": str(item["title"])[:255],
                "description": str(item.get("description", "")),
                "priority": priority,
                "due_date": due,
            }
        )
    return cleaned


def generate_tasks(
    *,
    workspace,
    document_id: str | None = None,
    text: str | None = None,
) -> dict:
    content = _resolve_content(workspace, document_id, text)
    messages = prompts.build_action_items_messages(content=content)

    cfg = get_llm_settings(workspace)
    provider = get_llm_provider(workspace)
    response = provider.generate(
        messages, temperature=0.1, max_tokens=cfg["max_tokens"]
    )
    return {"suggestions": _parse(response.text), "model": response.model}
