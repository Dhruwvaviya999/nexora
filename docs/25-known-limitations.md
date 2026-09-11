# 25 — Known Limitations & Technical Debt

[← Back to index](README.md)

Everything here was found in the code. Severity is **impact if left unfixed**,
not difficulty.

---

## Summary

**Six items from the original list have been fixed** (plus one new finding that
raising them surfaced). The table marks status.

| # | Item | Severity | Status |
|---|---|---|---|
| 1 | Non-httpOnly token cookies | 🔴 | ✅ **Fixed** |
| 2 | Uploaded files unserveable in production | 🔴 | ✅ **Fixed** |
| 2b | Uploads publicly readable via `/media/` | 🔴 | ✅ **Fixed** (new finding) |
| 3 | No file upload size/type limits | 🟠 | ✅ **Fixed** |
| 4 | No error boundary; infinite spinners | 🟠 | ✅ **Fixed** |
| 5 | Document list N+1 (2 queries per row) | 🟠 | Open |
| 6 | No database connection pooling | 🟠 | Open |
| 7 | Five backend test files empty | 🟠 | ✅ **Fixed** (six written) |
| 7b | Upload without a title always 400'd | 🟠 | ✅ **Fixed** (found by the new tests) |
| 8 | No `completed_at` — analytics approximates | 🟠 | Open |
| 9 | Two pending handovers per task possible | 🟠 | Open |
| 10 | `Comment.author` / `Workspace.owner` cascade | 🟠 | Open |
| 11 | Edge guard covered 2 of 12 route trees | 🟠 | ✅ **Fixed** |
| 12 | JWT blacklist never pruned; no scheduler | 🟠 | ✅ **Fixed** |
| 13 | No logging config, no error tracking | 🟠 | Open |
| 14 | Dashboard fires 15+ queries | 🟡 | Open |
| 15 | Duplicated role logic in three places | 🟡 | Open |
| 16 | Frontend types hand-mirrored | 🟡 | Open |
| 17 | Filter state not in the URL | 🟡 | Open |
| 18 | Slug check-then-act race | 🟡 | Open |
| 19 | Dead fields | 🟡 | Open |
| 20 | Documentation drift | 🟡 | Partly — these docs updated |
| 21 | Unused code | 🟢 | Open |

Fixed items are kept below with a short record of what changed, so the
reasoning survives. Full detail for the security ones is in
[18-security.md](18-security.md).

---

## ✅ Fixed

### 1. Non-httpOnly token cookies

Refresh token moved into a backend-issued httpOnly cookie; access token is now
memory-only. `proxy.ts` reads a value-less `nexora.session` marker instead of a
credential. See [18-security.md § 3.1](18-security.md).

### 2 / 2b. Uploads: unserveable in production, and publicly readable

Both were the same root cause — `file_url` pointed at `MEDIA_URL`. It now points
at `GET /documents/{id}/download/`, which applies the workspace-membership
filter, streams the file, and forces `Content-Disposition: attachment`. Works
identically with `DEBUG=False` and with S3 (`USE_S3=True`). WhiteNoise plus a
`collectstatic` step in the Dockerfile fixes the unstyled-admin gap at the same
time.

**2b was not on the original list.** Fixing "files 404 in production" surfaced
that they were *world-readable* in development — a cross-tenant read that
bypassed every permission check.

### 3. Upload size and type limits

`DocumentSerializer.validate_file`: 25 MB cap (`MAX_UPLOAD_SIZE`) and an
extension allow-list. `.html` / `.svg` / `.exe` rejected.

### 4. No error boundary

Added `app/error.tsx`, `app/(app)/error.tsx` (keeps the sidebar), and
`app/global-error.tsx` for root-layout failures. Eight pages that did
`if (isLoading || !data) return <Spinner/>` now branch on `isError` first and
render a shared `<ErrorState/>` with a retry button.

### 7. Empty test files

Six written: `common` (tenancy + role matrix + maintenance tasks), `tasks`,
`projects`, `comments`, `mentions`, `documents`. See
[26-testing.md](26-testing.md).

### 7b. Upload without a title always returned 400

Found by the new tests. `Document.title` has no `blank=True`, so DRF inferred
`required=True` — which made the filename fallback in `create()` unreachable.
The frontend only sends a title when the user types one, so those uploads had
been failing. Fixed with `extra_kwargs`.

### 11. Edge guard coverage

All twelve authenticated route trees now matched, not two.

### 12. No scheduler

`CELERY_BEAT_SCHEDULE` + a `beat` compose service + four idempotent pruning
tasks.

---

## Still open

## 5. 🟠 Document list N+1

**Where:** `backend/apps/documents/serializers.py:60-66`

`get_embedding_status` and `get_chunk_count` each issue one query per row. A
20-document page is 41 queries.

**Fix:** `.annotate(Count("chunks"))` plus a `Prefetch` of the latest embedding
job. See [19-performance-scalability.md](19-performance-scalability.md).

The same pattern (cheaper, but present) affects `member_count`, `task_count` and
`reply_count`.

---
## 6. 🟠 No connection pooling

`CONN_MAX_AGE` is unset — verified — so Django's default `0` applies and every
request opens a new PostgreSQL connection. No PgBouncer.

**Fix:** `CONN_MAX_AGE = 60`. One line.

---
## 8. 🟠 No `completed_at` column

**Where:** `backend/apps/core/views.py:167-169` (the docstring admits it)

Analytics infers completion week from `updated_at`. Editing a task completed
months ago moves it into the current week's bar.

**Fix:** add `completed_at`, set it on the transition into `completed`, clear it
on the transition out. One migration plus a serializer/model hook.

---
## 9. 🟠 Two pending handovers per task are possible

Nothing in `HandoverSerializer` or `HandoverViewSet` checks for an existing
pending handover on the same task. Two could be submitted and approved in
sequence, the second silently overwriting the first's assignment.

Related: the submitter is not required to be the task's current assignee — anyone
in the workspace can hand over anyone's task.

**Fix:** a `validate()` check for an existing `pending` handover on the task, or a
partial unique constraint.

---
## 10. 🟠 Cascade deletes on user

| FK | Behaviour | Problem |
|---|---|---|
| `Comment.author` | `CASCADE` | Deleting a user erases their comments **and**, via `Comment.parent` cascade, other people's replies underneath |
| `Workspace.owner` | `CASCADE` | Deleting a user destroys every workspace they own and all its content |

Every other user reference in the codebase is `SET_NULL`. These two are the
exceptions.

**Fix:** `Comment.author` → `SET_NULL` (the serializer already tolerates a null
author shape). For workspaces, either block deletion of a user who owns
workspaces, or force an ownership transfer first.

---
## 13. 🟠 No logging config, no error tracking

Verified: no `LOGGING` dict anywhere in `backend/config/`. No Sentry, no
correlation ids. A production 500 is invisible unless someone reads container
logs.

**Fix:** a `LOGGING` config with JSON output, plus an error tracker.

---
## 14. 🟡 Dashboard query count

Ten `.count()` calls plus four list queries, on the first screen every user
loads. Collapsible into two `aggregate()` calls. See
[19-performance-scalability.md](19-performance-scalability.md).

---
## 15. 🟡 Duplicated role logic

`IsWorkspaceAdmin` and `IsWorkspaceManager` exist in
`apps/common/permissions.py` but **no view uses them**. The same logic is written
inline in three places:

- `HandoverViewSet._reviewer_membership` (`views.py:40-45`)
- `InvitationViewSet._is_admin` (`views.py:66-71`)
- `resolve_workspace(require_admin=True)` (`ai/permissions.py:27-31`)

Behaviour is correct and consistent today. The risk is drift: change
`REVIEWER_ROLES` and you must remember three call sites.

**Fix:** use the permission classes where the object is available; keep the
helper for the AI case where the workspace arrives in the body.

---
## 16. 🟡 Frontend types are hand-mirrored

`frontend/src/types/*.ts` restate the DRF serializers by hand. There is no
generation from `/api/schema/` even though drf-spectacular is installed and
serving it.

**Mitigation that exists:** `pnpm typecheck` in CI catches the frontend half of a
drift.

**Fix:** generate types with `openapi-typescript` from the live schema as a
prebuild step.

---
## 17. 🟡 Filter state is not in the URL

Status, priority, assignee, search text and page number live in `useState`.
Filtered views cannot be bookmarked or shared, and a refresh resets them.

**Fix:** `useSearchParams` + `router.replace` on filter change.

---
## 18. 🟡 Slug check-then-act race

`_generate_unique_slug` queries, then saves. Two concurrent creates with the same
name both see the slug free. The unique constraint prevents bad data, so the
failure mode is an uncaught `IntegrityError` → 500.

**Fix:** a bounded retry loop around save on `IntegrityError`.

---
## 19. 🟡 Dead fields

| Field | Status |
|---|---|
| `Task.start_date` | Stored; no view, filter or UI reads it |
| `Task.estimated_hours` | Stored; unused |
| `Task.labels` | Stored; **not filterable** — no FilterSet entry |
| `User.first_name` / `last_name` | Inherited from `AbstractUser`; `name` is used instead |
| `AIMessage.token_count` | Always written as `0` |
| `AISettings.embedding_provider` / `embedding_model` | Stored but **never read** — `embeddings/factory.py` uses `settings.AI` |

The AI settings pair is the notable one: per-workspace embedding configuration
appears to be supported by the UI and model but is **not implemented**. It is
also arguably correct not to implement it, since the vector column dimension is
fixed database-wide.

---
## 20. 🟡 Documentation drift

| Claim | Reality |
|---|---|
| Root `README.md` says the route guard is `middleware.ts` | The file is `src/proxy.ts` (Next.js 16 rename). No `middleware.ts` exists |
| `app/(app)/layout.tsx:28` comment says "Middleware guards routes at the edge" | Same rename; also overstates coverage (2 of 12 route trees) |
| `apps/knowledge/handlers.py:9` says "Processing runs inline today (no Celery yet)" | **Stale.** `processor.py:47` calls `process_document_task.delay()` — Celery is wired |
| `config/settings/base.py:152-153` says "No auth *logic* is implemented yet" | Stale — a phase-1 comment; full auth exists |
| `config/settings/base.py:294` says "SimpleJWT (configuration only — endpoints arrive in Phase 2)" | Stale |
| Root `README.md` says "89 tests" | `grep -c "def test_"` across the suite returns **93** methods. The suite was not run to confirm which number the runner reports |
| `frontend/src/app/page.tsx:20` badge says "Phase 1 · Foundation ready" and cards say "Coming in a future phase" | The landing page still advertises an unfinished product |

None affect behaviour. All would confuse a new developer.

---
## 21. 🟢 Unused code

| Item | Note |
|---|---|
| `BaseLLMProvider.stream()` and both real implementations | Fully written; no view calls it. The base docstring calls it "the SSE upgrade path" |
| `IsWorkspaceAdmin`, `IsWorkspaceManager` | Defined, exported, never referenced by a view |
| `gunicorn==23.0.0` | In requirements; no command uses it (the Dockerfile explains why uvicorn is used instead) |
| `NotificationType.TASK_UPDATED` | Defined; never emitted |
| `frontend/src/components/layout/app-header.tsx` and `user-nav.tsx` | Not imported by any page — `app-sidebar` + `nav-user` are used instead. *Not confirmed whether these are dead or intentionally kept.* |

---

## What to fix first

The original one-day list is now mostly done. What remains, in order:

1. **`CONN_MAX_AGE = 60`** — 5 minutes, and it is the first thing that breaks
   under load.
2. **Document list N+1** — `annotate` + `Prefetch`, 41 queries to 3. Lock it in
   with `assertNumQueries`, which nothing currently uses.
3. **Collapse the dashboard's 10 counts** into two `aggregate()` calls.
4. **`LOGGING` config + an error tracker** — without it, none of the controls
   added in this pass can be observed failing.
5. **Wrap `HandoverViewSet.review` in a transaction**, and add the missing
   "one pending handover per task" rule.
6. **Add `completed_at`** so analytics stops approximating.

Items 1–3 are under two hours and halve the query count of the two most-loaded
pages.
