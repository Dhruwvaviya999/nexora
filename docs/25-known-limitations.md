# 25 — Known Limitations & Technical Debt

[← Back to index](README.md)

Everything here was found in the code. Severity is **impact if left unfixed**,
not difficulty.

---

## Summary

| # | Item | Severity | Area |
|---|---|---|---|
| 1 | Non-httpOnly token cookies | 🔴 High | Security |
| 2 | Uploaded files unserveable in production | 🔴 High | Deployment |
| 3 | No file upload size/type limits | 🟠 Medium-High | Security |
| 4 | No error boundary; failed fetches show infinite spinners | 🟠 Medium-High | Reliability |
| 5 | Document list N+1 (2 queries per row) | 🟠 Medium-High | Performance |
| 6 | No database connection pooling | 🟠 Medium-High | Performance |
| 7 | Five backend test files are empty | 🟠 Medium | Testing |
| 8 | No `completed_at` — analytics approximates | 🟠 Medium | Correctness |
| 9 | Two pending handovers per task are possible | 🟠 Medium | Business logic |
| 10 | `Comment.author` and `Workspace.owner` cascade on user delete | 🟠 Medium | Data integrity |
| 11 | Edge guard covers only 2 of 12 route trees | 🟠 Medium | Security/UX |
| 12 | JWT blacklist never pruned; no scheduler at all | 🟠 Medium | Operations |
| 13 | No logging config, no error tracking | 🟠 Medium | Operations |
| 14 | Dashboard fires 15+ queries | 🟡 Low-Medium | Performance |
| 15 | Duplicated role logic in three places | 🟡 Low-Medium | Maintainability |
| 16 | Frontend types hand-mirrored from serializers | 🟡 Low-Medium | Maintainability |
| 17 | Filter state not in the URL | 🟡 Low | UX |
| 18 | Slug generation has a check-then-act race | 🟡 Low | Correctness |
| 19 | Dead fields: `start_date`, `estimated_hours`, `labels`, `first_name`/`last_name` | 🟡 Low | Cleanliness |
| 20 | Documentation drift (5 items) | 🟡 Low | Docs |
| 21 | Unused code: `stream()`, `IsWorkspaceAdmin`, `gunicorn`, `TASK_UPDATED` | 🟢 Cosmetic | Cleanliness |

---

## 1. 🔴 Non-httpOnly token cookies

**Where:** `frontend/src/lib/auth/token-storage.ts:12,18`

Both tokens are set by JavaScript with `path=/; SameSite=Lax` — no `HttpOnly`, no
`Secure`. Any XSS on the frontend origin reads both, and the refresh token is
valid for 7 days.

**Why it exists:** so `src/proxy.ts` can read them server-side at the edge. The
file documents the trade-off itself.

**Mitigating:** no `dangerouslySetInnerHTML` anywhere (verified), React escapes
by default, and no user-supplied HTML rendering path exists.

**Fix:** backend sets an httpOnly refresh cookie on login; access token held in
memory only; a refresh endpoint reads the cookie. This also removes the reason
`proxy.ts` needs tokens. Meanwhile, add `; Secure` when the page is HTTPS — that
part is a one-line change.

---

## 2. 🔴 Uploaded files are unserveable in production

**Where:** `backend/config/urls.py:54-55`

`/media/` is served only when `DEBUG=True`. In production `DEBUG` is `False`,
`STORAGES` is the default `FileSystemStorage`, and the repository contains no
Nginx config and no `django-storages` configuration.

**Result:** `DocumentSerializer.get_file_url` returns a URL that 404s.

**Fix:** `django-storages` + S3 (the `Document` model docstring already
anticipates this), or a reverse proxy serving `/media/` from the shared volume.

---

## 3. 🟠 No upload restrictions

No size limit (`DATA_UPLOAD_MAX_MEMORY_SIZE` / `FILE_UPLOAD_MAX_MEMORY_SIZE` are
not overridden), no MIME whitelist, no `Content-Disposition` on serve. Only
*extraction* is restricted by extension.

**Fix:** a `validate_file` on `DocumentSerializer` checking size and extension;
serve with `Content-Disposition: attachment`.

---

## 4. 🟠 No error boundary; failed fetches show infinite spinners

**Where:** no `error.tsx` anywhere in `frontend/src/app/`, no React error
boundary component, and detail pages use:

```ts
if (isLoading || !handover) return <Loader2 className="animate-spin" />;
```
`app/(app)/handovers/[id]/page.tsx:72-78`

A failed fetch is indistinguishable from a slow one, and a render-time exception
blanks the page entirely.

**Fix:** add `app/error.tsx` and `app/(app)/error.tsx`, and branch on `isError`
in detail pages. Small change, large perceived-reliability improvement.

---

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

## 7. 🟠 Five backend test files are empty

Confirmed with `wc -l`:

```
apps/comments/tests.py    0 lines
apps/documents/tests.py   0 lines
apps/mentions/tests.py    0 lines
apps/projects/tests.py    0 lines
apps/tasks/tests.py       0 lines
apps/common/tests.py      0 lines
```

**Tasks and projects are the two most-used models in the product, and neither has
a dedicated test file.** They get incidental coverage from
`apps/core/tests_smoke.py`, which walks every API area, but there is nothing
testing e.g. that a task's workspace is derived from its project, or that a
non-member assignee is rejected.

`comments` and `mentions` are worse: the mention-parsing regex and the idempotent
sync are subtle logic with **zero** direct tests.

**Fix:** the highest-value missing tests are listed in
[26-testing.md](26-testing.md).

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

## 11. 🟠 Edge guard coverage

`src/proxy.ts` matcher covers `/dashboard/*`, `/workspaces/*`, `/login`,
`/register`. Ten other authenticated route trees — `/tasks`, `/projects`,
`/handovers`, `/documents`, `/ai/*`, `/activity`, `/search`, `/settings`,
`/notifications`, `/invitations` — rely only on the client-side layout gate.

No data leaks (no token means every API call 401s), but the experience is a
flash-then-redirect instead of a clean edge redirect, and the protection story is
inconsistent.

**Fix:** extend the matcher, or invert it to everything-except-public.

---

## 12. 🟠 No scheduler; blacklist grows forever

Verified: **no Celery beat schedule exists anywhere in the project code.**

`token_blacklist_outstandingtoken` gains a row on every refresh — with 15-minute
tokens, hundreds per active user per week — and it is read on every token
validation. SimpleJWT ships `manage.py flushexpiredtokens`; nothing runs it.

Also unswept: expired invitations (status only flips on an accept attempt), old
`EmbeddingJob` rows, and `ai_searchhistory`.

**Fix:** add a `beat` service and schedule `flushexpiredtokens` daily.

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

If you had one day:

1. `CONN_MAX_AGE = 60` (5 minutes)
2. `; Secure` on cookies when HTTPS (5 minutes)
3. Extend the `proxy.ts` matcher (10 minutes)
4. `app/error.tsx` + `isError` branches (1 hour)
5. Fix the document N+1 with `annotate` + `Prefetch` (1 hour)
6. Collapse the dashboard counts into aggregates (1 hour)
7. Upload size + extension validation (30 minutes)
8. Write `apps/tasks/tests.py` and `apps/projects/tests.py` (2 hours)

That list removes both High-severity performance items, the worst reliability
gap, two of the security items, and the most conspicuous testing hole.

---

**Next:** [26 — Testing](26-testing.md)
