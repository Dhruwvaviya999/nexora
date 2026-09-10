# API — AI Assistant

[← API index](README.md) · [Module deep dive](../modules/ai-assistant.md)

Base `/api/v1/ai/` · `backend/apps/ai/views.py`

**Every action endpoint takes the workspace in the request body**, not the URL,
so DRF object permissions cannot apply. Each one calls `resolve_workspace()`
first — the file's own comment calls it *"the isolation gate"*.

```python
def resolve_workspace(user, workspace_id, *, require_admin: bool = False):
    workspace = Workspace.objects.filter(pk=workspace_id).first()
    if workspace is None:                     raise NotFound("Workspace not found.")
    member = workspace.members.filter(user=user).first()
    if member is None:                        raise PermissionDenied("You are not a member of this workspace.")
    if require_admin and member.role not in (OWNER, ADMIN):
        raise PermissionDenied("You must be a workspace admin.")
    return workspace
```
`backend/apps/ai/permissions.py:15-33`

> This returns **404** for a nonexistent workspace and **403** for one you are not
> in — unlike the rest of the API, which returns 404 for both. A minor
> information leak, noted in [18-security.md](../18-security.md).

All four action endpoints carry `throttle_classes = [AIRateThrottle]` — **30/hour
per user**, because *"LLM calls cost money per request."*

---

## `POST /ai/chat/`

The full RAG turn.

**Request**
```json
{ "workspace": "<uuid>",
  "message": "What is still outstanding on the billing migration?",
  "conversation": "<uuid>"          // optional; omit to start a new thread
}
```

**Response `200`**
```json
{ "conversation": "<uuid>",
  "message": {
    "id": "<uuid>", "role": "assistant",
    "content": "Three items remain...",
    "sources": [
      { "chunk_id": "<uuid>", "document_id": "<uuid>",
        "title": "Q3 runbook.pdf", "content": "...", "chunk_index": 4,
        "score": 0.72 }
    ],
    "created_at": "..."
  },
  "confidence": "high" }
```

**What happens, in order** (`ChatView.post`, `views.py:145-227`):

1. `AIRateThrottle`
2. `resolve_workspace(request.user, data["workspace"])`
3. Get or create the conversation. New ones get `title = message[:80]` and
   `created_by`/`updated_by = user`. An unknown `conversation` id → `404
   "Conversation not found."` (scoped to this user **and** workspace)
4. **Persist the user's `AIMessage` first** — *"so history is consistent on
   failure"*
5. Fetch the last 10 turns (`_HISTORY_TURNS`), oldest-first
6. `rag.answer_question(workspace=..., query=..., history=...)`
7. Persist the assistant `AIMessage` with `sources` and
   `metadata = {confidence, top_score, model}`
8. `conversation.save(update_fields=["updated_at"])` so it sorts to the top

**Errors**

| Status | When |
|---|---|
| `403` | Not a workspace member |
| `404` | Workspace or conversation not found |
| `429` | Over 30 AI calls this hour |
| `502` | `ProviderError` — missing API key, provider API failure, or AI disabled |
| `503` | `DatabaseError` during retrieval — pgvector or the migration is missing |

The 503 body is deliberately actionable:

> "Semantic search isn't available yet. The vector index has not been set up for
> this deployment — ask an admin to finish AI setup (install pgvector and run
> migrations)."

**Confidence** — `high` if `top_score >= 0.6`; `medium` if `>= 0.4` or structured
context was present; else `low`.

---

## `POST /ai/search/`

Retrieval only — **no LLM call**, so no provider key is needed.

**Request**
```json
{ "workspace": "<uuid>", "query": "webhook retry policy", "limit": 6 }
```

**Response `200`**
```json
{ "query": "webhook retry policy",
  "results": [ { "chunk_id": "...", "document_id": "...", "title": "...",
                 "content": "...", "chunk_index": 4, "score": 0.71 } ],
  "count": 1, "top_score": 0.71 }
```

`score = round(max(0, 1 - cosine_distance), 4)`.

**Side effect:** every search writes a `SearchHistory` row (query truncated to
1000 chars, `results_count`, `top_score`). That powers the "recent queries" UI —
and means **raw query text is stored**, which is a privacy consideration.

Still throttled at 30/hour even without an LLM call, because embedding the query
is CPU-bound.

Empty results are normal: chunks beyond `AI_SEARCH_MAX_DISTANCE` (0.75) are
dropped entirely.

---

## `POST /ai/summarize/`

**Request**
```json
{ "workspace": "<uuid>", "target_type": "project", "target_id": "<uuid>" }
```
or, for activity:
```json
{ "workspace": "<uuid>", "target_type": "activity", "period": "week" }
```

`target_type` ∈ `project` · `task` · `document` · `activity`.
`period` ∈ `day` (1) · `week` (7) · `month` (30) — default `week`.

**Response `200`**
```json
{ "summary": "## Status\n\n- ...", "target_type": "project", "model": "gemini-3.6-flash" }
```

Markdown, because the persona prompt asks for short markdown sections.

**What gets gathered** (all workspace-scoped, `services/summarizer.py`):

| Target | Content |
|---|---|
| `project` | Name, status, description, task count, then up to 50 tasks with status + assignee |
| `task` | Title, project, status, priority, assignee, due date, description |
| `document` | The first 40 chunks |
| `activity` | Up to 200 activity rows over the period |

**Errors**

| Status | When |
|---|---|
| `400` | `SummaryError` — invalid `target_type`, missing `target_id`, object not in this workspace, or *"This document has not been processed yet — try again shortly."* |
| `502` | `ProviderError` |

---

## `POST /ai/generate-tasks/`

Extracts action items. **Nothing is persisted.**

**Request** — one of:
```json
{ "workspace": "<uuid>", "document": "<uuid>" }
{ "workspace": "<uuid>", "text": "Meeting notes: ..." }
```

**Response `200`**
```json
{ "suggestions": [
    { "title": "Add retry logic to the webhook handler",
      "description": "Currently fails silently on 5xx.",
      "priority": "high",
      "due_date": "2026-09-20" } ],
  "model": "gemini-3.6-flash" }
```

**The model's output is treated as untrusted input.** `_parse`
(`services/action_items.py:51-81`) regexes the JSON array out of any surrounding
prose, parses it in a `try`, checks it is a list, checks each item is a dict with
a `title`, coerces `priority` to a valid `TaskPriority` (defaulting to `medium`),
nulls any `due_date` that is not `YYYY-MM-DD`, and truncates the title to 255.

Unparseable output yields `{"suggestions": []}` — never an error.

**The design decision:** the docstring is explicit — *"The tasks are NOT persisted
here — they're returned for the user to review and approve, after which the
frontend creates them through the existing Task API."* The LLM never writes to the
database, and every created task passes the same validation as a manual one.

`_VALID_PRIORITIES` is kept identical to `apps.tasks.models.TaskPriority` *"so
approved suggestions are accepted by the existing Task create endpoint."*

**Errors** — `400` `ActionItemError` (no document/text, document not in this
workspace, document not yet processed) · `502` `ProviderError`

---

## `GET /ai/settings/?workspace=<uuid>`

**Auth:** member. Created lazily with `get_or_create` on first read.

```json
{ "workspace": "<uuid>", "is_enabled": true,
  "provider": "gemini", "chat_model": "gemini-3.6-flash",
  "embedding_provider": "sentence_transformer",
  "embedding_model": "all-MiniLM-L6-v2",
  "temperature": 0.2, "max_tokens": 1024,
  "has_api_key": true }
```

**The plaintext key is never returned** — only `has_api_key`.

## `PATCH /ai/settings/`

**Auth: owner / admin** — `resolve_workspace(..., require_admin=True)`.

**Request** `{ "workspace": "<uuid>", "provider": "openai",
"chat_model": "gpt-4o-mini", "temperature": 0.3, "api_key": "<hidden>" }`

The key is Fernet-encrypted into `api_key_encrypted`
(`services/crypto.py`). `decrypt()` swallows failures and returns `""`, so a
rotated key degrades to "no key configured".

> `embedding_provider` and `embedding_model` are **stored but never read** —
> `knowledge/embeddings/factory.py` uses `settings.AI`. Per-workspace embedding
> configuration is not implemented.

**Errors** — `400` missing `workspace` · `403` not admin · `404` workspace not
found

---

## Resource ViewSets

### `/ai/conversations/`

`ListModelMixin`, `RetrieveModelMixin`, `DestroyModelMixin` — **no create**
(that happens through `/ai/chat/`).

```python
AIConversation.objects.filter(user=self.request.user,
                              workspace__members__user=self.request.user).distinct()
```

**Conversations are private to their owner** — a workspace admin cannot read
someone else's chat.

`?workspace=` filter · ordering `-updated_at`.
`retrieve` uses `AIConversationDetailSerializer`, which includes the messages;
`list` uses the lighter one.

### `/ai/search-history/`

List only. Scoped to `user=request.user` and workspace membership.
`?workspace=` · ordering `-created_at`.

### `/ai/prompt-templates/`

Full CRUD via `WorkspaceScopedViewSet`, with one extra narrowing:

```python
def get_queryset(self):
    qs = super().get_queryset()
    return qs.filter(Q(is_shared=True) | Q(created_by=self.request.user))
```

Shared templates are visible workspace-wide; private ones only to their author.

Filters: `workspace`, `category` · Search: `name`, `description` ·
Ordering: `name`, `created_at`

---

## Hooks reference

All in `frontend/src/hooks/use-ai.ts`:

| Hook | Endpoint |
|---|---|
| `useConversations`, `useConversation`, `useDeleteConversation` | `/ai/conversations/` |
| `useSemanticSearch` | `POST /ai/search/` |
| `useSearchHistory` | `/ai/search-history/` |
| `usePromptTemplates` + create/update/delete | `/ai/prompt-templates/` |
| `useAISettings`, `useUpdateAISettings` | `/ai/settings/` |

Chat is driven from `components/ai/chat-window.tsx`.
