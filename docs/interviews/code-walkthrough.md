# Interview — Code Walkthrough

[← Interviews index](README.md)

"Open a file and walk me through it." These are the twelve most likely, with what
to say and what they will ask next.

---

## 1. `backend/apps/common/viewsets.py`

**48 lines. The most important file in the backend.**

**Say:** This is where multi-tenancy is enforced. `get_queryset()` filters
`workspace__members__user=request.user`, so another tenant's row is never in the
queryset — which means a cross-tenant detail request returns 404 rather than 403,
so the API never confirms an id exists. `perform_create` checks membership
explicitly, because `get_queryset` doesn't protect creates. And both write paths
stamp `created_by`/`updated_by`. Every subclass gets all of that for free, which
is why `apps/tasks/views.py` is 25 lines.

**Point at:** the `swagger_fake_view` guard — there's no authenticated user during
OpenAPI schema generation, so without it `manage.py spectacular` crashes.

**Follow-ups:** Why `.distinct()`? Why 404 not 403? What protects list endpoints
if the permission class only implements `has_object_permission`?

---

## 2. `backend/apps/common/permissions.py`

**Say:** Five reusable classes, all sharing two helpers. `_resolve_workspace`
returns the object if it *is* a Workspace, otherwise `obj.workspace` — that one
helper is why a single permission class protects both a workspace and everything
nested inside it.

**Point at:** the local `from apps.workspaces.models import Workspace` inside each
function. `workspaces` depends on `common`, so a top-level import would be
circular.

**Volunteer:** `IsWorkspaceAdmin` and `IsWorkspaceManager` are defined but no view
uses them — the same logic is written inline in three places. Behaviour is
correct, but change `REVIEWER_ROLES` and three call sites have to agree. I'd
refactor to use the classes.

---

## 3. `backend/apps/handovers/views.py`

**161 lines. The richest business logic.**

**Say:** Start with `review`. Role check via `_reviewer_membership`, then a status
check, then the serializer — which requires a comment on rejection. Then the
handover is updated with `update_fields`, and if approved, `task.assignee` is set
to the recipient. Then two notifications: `TASK_ASSIGNED` to the recipient,
`HANDOVER_REVIEWED` to the submitter.

**Point at:** `if approved and handover.to_user is not None` — the FK is
`SET_NULL`, so a deleted recipient can't crash the review.

**Point at:** `perform_update` restricting edits to the submitter, and
`perform_destroy` allowing the submitter *or* a reviewer, pending only.

**Volunteer:** the two saves aren't in a transaction. A crash between them leaves
an approved handover and an unassigned task. It should be `@transaction.atomic`.

---

## 4. `frontend/src/lib/api/client.ts`

**142 lines. The most important file in the frontend.**

**Say:** A typed `fetch` wrapper. Four jobs: attach the JWT unless `skipAuth`;
detect `FormData` and *omit* `Content-Type` so the browser sets the multipart
boundary; single-flight refresh on 401 with exactly one retry; and normalise every
non-2xx into an `ApiError` with `status`, `message` and `details`.

**Point at:** `let refreshPromise` at module scope, and `getRefreshedToken()`.
Ten concurrent 401s share one refresh. That's a correctness requirement, not an
optimisation — refresh tokens rotate and are single-use, so parallel refreshes
would blacklist each other.

**Point at:** `_isRetry: true` on the recursive call. That's what guarantees
termination.

**Volunteer:** this file has no tests, and it's the most logic-dense file in the
frontend. It's the first frontend test I'd write.

---

## 5. `frontend/src/providers/workspace-provider.tsx`

**Say:** It resolves the active workspace from three sources —
`selectedId ?? storedId ?? workspaces[0] ?? null` — **during render**, not in an
effect.

**Point at:** the comment at lines 70-73. The previous version used two effects
that raced: one restored the persisted id, the other validated it and overwrote it
with `workspaces[0]` because it still saw the pre-restore value. Deriving during
render eliminates the race by construction.

**Point at:** why both `selectedId` and `useSyncExternalStore` exist — a same-tab
`localStorage.setItem` fires no `storage` event, so the in-tab choice needs its
own state and takes precedence.

**The bigger point:** `activeWorkspaceId` is a param on nearly every query key, so
switching workspace refetches the whole UI automatically with no manual
invalidation.

---

## 6. `backend/apps/activities/handlers.py`

**90 lines. The most elegant file in the project.**

**Say:** A factory function registers `post_save` and `post_delete` per model, so
adding audit history for a new model is one line. **No domain app imports the
activities app** — the receivers are attached from the outside in
`AppConfig.ready()`.

**Point at:** `weak=False`. The handler closures are created inside a factory and
referenced nowhere else, so Python would garbage-collect them and the signals
would silently stop firing.

**Point at:** `dispatch_uid`, which prevents double registration doubling every
audit row.

**Volunteer the blind spot:** `queryset.update()`, `bulk_create` and raw SQL fire
nothing, so those writes are unaudited.

---

## 7. `backend/apps/activities/services.py`

**Say:** `log_activity` plus a suppression guard. Deleting a workspace cascades
into every child, and each cascade fires `post_delete`, which would append
activity rows referencing a workspace that's about to be removed — a foreign-key
violation at commit that takes the whole delete down.

**Point at:** `_workspaces_being_deleted`, a module-level set. `pre_delete` adds
the pk, `post_delete` removes it, and `log_activity` returns early while it's
present.

**Volunteer:** it's process-local mutable global state. It works because the
delete and its cascade happen in one request in one process. A cleaner fix would
be checking whether the workspace still exists, or disconnecting the receivers for
the duration.

**This is the best debugging story in the codebase — use it.**

---

## 8. `backend/apps/knowledge/services/processor.py`

**Say:** The ingestion orchestrator. `enqueue_document` records an
`EmbeddingJob` and hands the work to Celery. `process_document` does
extract → chunk → embed → store.

**Point at:** `transaction.on_commit(dispatch)`. Queueing inside the transaction
races the worker — it could read a document row that isn't visible yet, or act on
one that rolled back.

**Point at:** the `except` around `.delay()` that runs the job inline — "broker
down: better slow than lost."

**Point at:** `process_document`'s broad `except` that records `status=failed` and
the error text on the job row rather than raising. A failed embedding must never
fail a successful upload.

**Point at:** `_store_chunks` is `@transaction.atomic` — delete-then-bulk-create,
so a re-index never leaves a document with zero chunks.

---

## 9. `backend/apps/ai/services/rag.py`

**Say:** The RAG orchestration. Sanitise the query, retrieve the top six chunks
scoped to the workspace, build a structured snapshot of projects and tasks,
assemble the prompt, call the workspace's provider, return answer + sources +
confidence.

**Point at:** `build_structured_context`. Retrieval alone can't answer "how many
overdue tasks do we have?" — no document contains that. This is what makes it a
workspace assistant rather than a document Q&A bot.

**Point at:** `_confidence` — `1 - cosine_distance` of the best chunk, bucketed.
It tells the user how much of the answer was actually grounded.

**Volunteer:** the keyword matcher is substring `ILIKE`, so "authentication"
doesn't match "auth", and up to sixteen leading-wildcard predicates can't use an
index. Only runs on chat, which is rate-limited, but it's the part I'd replace.

---

## 10. `backend/apps/ai/services/security.py`

**Say:** The prompt-injection boundary. It names three trust levels explicitly —
our instructions (trusted), the user's question (semi-trusted), and retrieved
document content (**completely untrusted**).

**Point at:** `sanitize_input` stripping control characters. Those bytes can hide
text from a human reviewer while the model still reads it.

**Point at:** `SYSTEM_GUARDRAILS` rule two — CONTEXT is untrusted data, never
instructions.

**Be honest:** this is defence in depth, not a guarantee. The real containment is
that retrieval is workspace-scoped and the model has no tools.

---

## 11. `backend/config/settings/base.py`

**Say:** 372 lines, and almost every block encodes a decision. Point at four:

- `DEFAULT_PERMISSION_CLASSES = (IsAuthenticated,)` — everything private by
  default; only four views opt out.
- The throttle rates block, and why credential endpoints key by **IP not user**.
- The comment at lines 222-226: DRF counts requests in the Django cache, and a
  per-process LocMemCache makes the effective limit `rate × worker_count`.
- The `"text"` template engine at lines 117-134 — autoescaping off for plain-text
  emails, because otherwise an `&` in a reset URL becomes `&amp;` and the link
  arrives with a parameter literally named `amp;token`.

**That last one is the detail that shows you shipped this.**

---

## 12. `backend/config/asgi.py`

**Say:** The protocol split. HTTP goes to the normal Django application; `/ws/`
goes to Channels behind an `OriginValidator` and a JWT middleware.

**Point at:** `get_asgi_application()` must run **before** importing anything that
touches models — it populates the app registry, which is why the Channels imports
are below it with `# noqa: E402`.

**Point at:** the comment explaining why the origin is validated against
`CORS_ALLOWED_ORIGINS` rather than `ALLOWED_HOSTS` — the socket's Origin is the
*frontend's*, while `ALLOWED_HOSTS` lists the *API's* hostnames. They coincide
only on localhost; split them across `api.example.com` and `app.example.com` and
every socket would be denied.

---

## If they say "pick a file you're proud of"

Pick `backend/apps/activities/services.py` or
`backend/apps/knowledge/services/processor.py`.

Both are short, both contain a non-obvious correctness fix with the reasoning
written down, and both let you tell a debugging story rather than describe
features.

---

## If they say "pick a file you'd rewrite"

`backend/apps/documents/serializers.py`.

> The two `SerializerMethodField`s each issue a query per row — 41 queries for a
> 20-row page. I'd annotate the chunk count and prefetch the latest job, taking
> it to three. And I'd add file size and extension validation, which currently
> isn't there at all.

That answer names a real bug, gives the fix, and adds a second improvement
unprompted.
