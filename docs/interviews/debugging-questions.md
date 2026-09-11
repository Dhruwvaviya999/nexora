# Interview — Debugging Scenarios (20)

[← Interviews index](README.md) · [Troubleshooting guide](../23-troubleshooting.md)

Interviewers use these to see whether you debug **systematically** or by guessing.
Say the method out loud, then narrow.

---

## The method, every time

```
1. Reproduce — exactly which user, workspace, page
2. Frontend state — React Query Devtools: which key, what data, is it stale?
3. Network — was the request sent? What params? What status?
4. Response — is the data wrong, or the rendering wrong?
5. View — read get_queryset(). Most "missing data" bugs live here
6. Serializer — is a SerializerMethodField computing something unexpected?
7. SQL — print(qs.query) or connection.queries
8. Database — query the table directly and compare
9. Signals — if a side effect is missing, does the write path even fire post_save?
10. Fix, then add a regression test
```

---

**1. "The dashboard shows 5 overdue tasks but I only see 3 in the list."**

Almost certainly a **definition mismatch**, not a bug.
`overdue_tasks = tasks.filter(due_date__lt=today, status__in=OPEN_TASK_STATUSES)`
where open is `todo`, `in_progress`, `review`. The `/tasks` page may be filtered
by project or assignee, or paginated to 20. Reproduce the dashboard query in the
shell, compare the ids, and check what filters the list page has applied.

**2. "I can't see a task my colleague shared with me."**

Check membership first:
`SELECT role FROM workspaces_workspacemember WHERE workspace_id=? AND user_id=?`
No row means the API returns 404 — by design, since `get_queryset()` filters by
membership. Then check whether they are in the same workspace at all: the same
task title can exist in two tenants.

**3. "Notifications stopped appearing in real time in production."**

Almost certainly the **channel layer**. With `InMemoryChannelLayer` and multiple
uvicorn workers, a push from worker A never reaches a socket on worker B. Check
`CHANNEL_LAYER_URL`/`REDIS_URL` is set so `channels_redis` is used.
Confirm the socket is even open: DevTools → Network → WS. If it is not, check
the origin (`OriginValidator` uses `CORS_ALLOWED_ORIGINS`) and whether the proxy
forwards the upgrade.
Note this is a *degradation*, not an outage — polling still updates every 30s.

**4. "Users are randomly logged out."**

Look at `POST /auth/refresh/` responses. A 401 there means the refresh token was
rejected. Reasons, in likelihood order: it was already used (rotation makes it
single-use, so a second concurrent refresh would blacklist it — but
`refreshPromise` should prevent that, so check it is actually module scope); a
password reset revoked every session; the 7-day lifetime expired; or `SECRET_KEY`
changed, which invalidates every token ever issued.

**5. "A document uploaded fine but AI search can't find it."**

Four checks, in order:
`SELECT COUNT(*) FROM knowledge_documentchunk WHERE document_id=?` — zero means
never embedded. Then `EmbeddingJob.status` and `.error` for that document. Then
whether the extension is supported — only `.pdf .docx .txt .md .markdown` are
processed, and unsupported files are skipped **silently**. Then whether it is a
scanned PDF: pypdf extracts nothing and there is **no OCR**.
Finally, the distance threshold — a genuinely unrelated query returns `[]`
because chunks beyond 0.75 cosine distance are dropped.

**6. "The audit log is missing an entry for a change I know happened."**

The write bypassed `post_save`. Check whether the code path used
`queryset.update()`, `bulk_create` or raw SQL — all of which fire no signals.
`NotificationViewSet.read_all` uses `.update()` deliberately. Then confirm the
model is actually registered in `activities/handlers.py` — only seven are.

**7. "Two users report seeing each other's AI conversations."**

I would treat this as a P0 and verify before anything else, because it should be
impossible: `AIConversationViewSet.get_queryset` filters
`user=self.request.user` **and** workspace membership.
Reproduce with two accounts and compare `AIConversation.user_id` in the database.
If the rows are correct, the bug is in the view or a caching layer — check
whether `queryClient.clear()` ran on logout, because stale cache from a previous
session on the same browser would look exactly like this.

**8. "The reviewer queue shows a handover that was already approved."**

Cache. `/handovers/reviews` uses `useHandovers({status:"pending"})`. If the
approval happened in another tab or by another user, this client's cache is stale
until `staleTime` (60s) expires. `useReviewHandover` invalidates
`["handovers"]` — but only in the tab that performed it. Confirm with React Query
Devtools that the key is stale, and check the database status to rule out a real
write failure.

**9. "Password reset emails aren't arriving."**

In development they do not "arrive" — the console backend prints them to the
**backend terminal**. In production: check `EMAIL_HOST` is set; check the Celery
worker logs, since `send_email_task` retries three times and logs failures; and
remember `send_templated_email` defaults to `fail_silently=True`, so an SMTP
outage is logged rather than surfaced.
If the email arrives but the link fails, look for `amp;token` in the URL — that
means the text body rendered through an escaping engine instead of the dedicated
`"text"` engine.

**10. "The whole app shows a spinner and never loads."**

`app/(app)/layout.tsx` renders a spinner while `isLoading || !isAuthenticated`.
So either the bootstrap refresh or `/auth/me/` never resolved — check the
Network tab for `POST /auth/refresh/` and `GET /auth/me/`. A render-time
exception would now be caught by `app/(app)/error.tsx` and shown as an error
card, so an endless spinner points at a pending request, not a crash.

**11. "A detail page spins forever but the list works."**

Detail pages now branch on `isError` **before** the loading guard and render
`<ErrorState/>`, so a failure shows the status-specific message and a retry
button. An endless spinner therefore means the request is genuinely still
pending — check the Network tab for a stalled call, and whether
`POST /auth/refresh/` is looping.

**12. "Creating a task returns 403 but I am definitely in the workspace."**

`_require_membership` uses the workspace derived from the **project**. So the
usual cause is a stale `activeWorkspaceId` in `localStorage` pointing at a
workspace you left, or a project from a different workspace being selected. Clear
`nexora.activeWorkspace` and reload. Confirm by comparing the project's
`workspace_id` with your memberships.

**13. "Analytics shows tasks completed in a week when nothing happened."**

Not a bug — a documented approximation. There is no `completed_at` column, so
"completed this week" means *"status is completed and `updated_at` falls in that
week"*. Someone edited an old completed task. The view docstring says exactly
this. The fix is a real `completed_at` column.

**14. "The document list page takes 4 seconds."**

The N+1. `get_embedding_status` and `get_chunk_count` each run one query per row —
41 queries for a 20-row page — and there is no connection pooling, so each
request also pays a fresh connection. Confirm with `connection.queries`, then fix
with `.annotate(Count("chunks"))` plus a `Prefetch` of the latest job, and lock it
in with `assertNumQueries`.

**15. "Creating a project sometimes returns 500."**

The slug race. `_generate_unique_slug` checks then saves; two concurrent creates
with the same name both see the slug free, and the unique constraint rejects the
second with an uncaught `IntegrityError`. Data stays correct — the error handling
does not. Fix with a bounded retry on `IntegrityError`.

**16. "AI chat returns 502 for one workspace but works for another."**

Provider configuration is **per workspace**. Check that workspace's `AISettings`:
`is_enabled`, `provider`, and whether `api_key_encrypted` is set. The 502 message
comes straight from the provider — "Gemini API key is not configured for this
workspace" is a different problem from a provider API error. Also check whether
`AI_FIELD_ENCRYPTION_KEY` changed, because `decrypt()` swallows failures and
returns `""`, which looks exactly like "no key configured".

**17. "After deploying, every API call from the browser fails."**

Two candidates. If it is a CORS error, the frontend origin is missing from
`CORS_ALLOWED_ORIGINS` — and note the same list gates websockets. If the requests
are going to a hostname that does not resolve, `NEXT_PUBLIC_API_URL` was baked in
as an internal service name; it is inlined at **build** time, so it needs a
rebuild, not a restart.

**18. "Uploaded documents 404 when you click to download — but only in
production."**

Not a bug in the upload; a deployment gap. `/media/` is served by Django **only
when `DEBUG=True`**, and there is no object storage and no reverse proxy
configured in this repository. `file_url` returns a URL nothing serves. The fix is
S3 via `django-storages`, or a proxy serving the volume.

**19. "A workspace delete times out and rolls back."**

That is the exact bug `_workspaces_being_deleted` was written to fix — cascade
`post_delete` handlers appending activity rows that reference the workspace being
removed, which fails as a foreign-key violation at commit. If it is happening
again, check that `pre_delete` on `Workspace` is still calling
`suppress_activity_for_workspace`. If it is a genuine timeout, the cascade is
simply large — thousands of chunks and activity rows — and I would delete in
batches or make it a background job.

**20. "Something is wrong but I don't know what. Where do you start?"**

`GET /api/v1/health/` — does the database respond? Then reproduce with a specific
account and workspace, and work down the ten-step ladder: frontend cache →
network → response → view queryset → serializer → SQL → table → signals.
For this codebase specifically, **the two most common root causes are a scoping
filter and a stale cache key.** I check those before anything else.

---

## Tools available in this project

| Tool | How |
|---|---|
| React Query Devtools | Already mounted in dev (`app/providers.tsx:47`) — inspect keys and staleness |
| Swagger UI | `/api/docs/` — authorise with a token and replay any request |
| Django admin | `/admin/` — every model is registered |
| Health check | `/api/v1/health/` |
| SQL for a queryset | `print(qs.query)` |
| Query count | `CaptureQueriesContext`, or `assertNumQueries` in a test |
| Container logs | `docker compose logs -f web` / `-f worker` — emails print here |
| Celery job state | `SELECT status, error FROM knowledge_embeddingjob ORDER BY created_at DESC` |

**Not** installed: `django-debug-toolbar`, Sentry, any structured logging.
Worth saying so — it is an honest gap and it is on the fix list.

---

**Next:** [Why did you do this?](why-did-you-do-this.md)
