# Interview — Senior / Architect Questions (20)

[← Interviews index](README.md)

These are the questions asked after someone has actually read the code. There is
no "correct" answer to most — they test judgement.

---

**1. Where are the biggest scalability risks in this system?**

In order:

1. **No connection pooling.** `CONN_MAX_AGE` is unset, so every request opens a
   PostgreSQL connection. `max_connections` is the ceiling and it arrives sooner
   than anything else.
2. **Local filesystem for uploads.** `MEDIA_ROOT` is a directory shared by web
   and worker through a Docker volume. Two hosts cannot share it — this blocks
   horizontal scaling outright.
3. **The embedding model in memory.** Each worker process holds ~90 MB+, which is
   why compose caps `--concurrency=2`.
4. **Live analytics.** Recomputed per request, cost linear in task count.
5. **Query counts** on the two most-loaded pages: 15+ on the dashboard, 41 on a
   20-row document list.

**2. What happens under concurrent updates to the same record?**

Last write wins. There is no optimistic locking — no version column, no
`ETag`/`If-Match`, no `select_for_update` anywhere. Two people editing the same
task overwrite each other silently.

Partially mitigated by `update_fields` on some saves, which narrows the columns
written — so two people editing *different* fields of a handover during review
would not clobber each other. But that is incidental, not a strategy.

The fix: a `version` integer bumped on save, checked in `perform_update`, 409 on
mismatch.

**3. Two managers open the same pending handover and both click Approve. What
happens?**

Both pass `_reviewer_membership`. Both read `status == pending`. The first writes
approved and reassigns the task; the second's check-then-act has already passed,
so it also writes — overwriting `reviewer`, `review_comment` and `reviewed_at`,
and firing a second set of notifications.

`select_for_update()` on `get_object()` inside a transaction would serialise it,
or a conditional update:
`Handover.objects.filter(pk=..., status=PENDING).update(...)` and check the
returned row count.

**4. How would you make this horizontally scalable?**

Five changes, all identified in the code:

1. **Redis is mandatory**, not optional — the in-memory channel layer means a
   push from process A never reaches a socket on process B, and the LocMem cache
   makes throttle limits `rate × worker_count`.
2. **Uploads to S3** via `django-storages` — this also fixes the production
   media-serving gap.
3. **Connection pooling** — PgBouncer in transaction mode.
4. **Migrations as a separate job**, not in the container start command.
5. **Session affinity is not needed** — JWT is stateless, which is the one thing
   already right.

The web tier and Celery workers then scale freely. PostgreSQL becomes the
bottleneck, addressed with read replicas for analytics.

**5. What would you cache, and where?**

| Target | Where | TTL | Why |
|---|---|---|---|
| `/analytics/` | Redis, keyed by workspace | 5–15 min | Expensive, not real-time |
| `/dashboard/` | Redis, keyed by (workspace, user) | 30–60 s | Highest-traffic endpoint |
| Workspace membership lookups | Per-request memo | request | Read on every permission check |
| Embedding vectors for repeated queries | Redis, keyed by query hash | hours | Skips a CPU-bound encode |

What **not** to cache: anything user-scoped without the user in the key, and the
notification unread count — the websocket already makes it cheap.

**6. Where is this system tightly coupled?**

Three places:

- `apps/core/views.py` imports models **and serializers** from six apps. It is the
  aggregation seam — acceptable for read-only views, but any serializer change
  there changes the dashboard response.
- `HandoverViewSet.review` writes `tasks_task` directly. Defensible, since
  approval is the authorisation point, but it is a hard dependency between two
  apps.
- The **mention token format** is duplicated between a React component and a
  Python regex, with nothing checking they agree. That is the most fragile
  coupling in the project.

**7. Where is it well decoupled?**

The audit log. No domain app imports `activities` — receivers are registered from
the outside in `AppConfig.ready()`, so adding history for a new model is one
line. The same pattern covers mentions and embedding kickoff.

Also the LLM provider abstraction: RAG, the summariser and action items talk only
to `BaseLLMProvider`, so swapping Gemini for OpenAI per workspace touches no
business logic.

**8. How would you test this properly?**

The order I would actually write them:

1. `apps/common/tests.py` — tenancy. A member of A gets 404 for B's task;
   `perform_create` rejects a foreign workspace; audit stamping works. **The
   single highest-value missing test.**
2. `lib/api/client.test.ts` — single-flight refresh, one retry,
   `skipAuth` behaviour, FormData headers, error normalisation. The most
   logic-dense frontend file and it has zero tests.
3. `apps/tasks/tests.py` — workspace derivation, non-member assignee rejection.
4. `apps/mentions/tests.py` — sync idempotency.
5. `assertNumQueries` around the dashboard and document list, to lock in the N+1
   fixes so they cannot regress.

**9. How would you handle database failures?**

Currently: `/health/` returns 503, and everything else 500s. There is no retry, no
circuit breaker, no read replica.

I would add connection retry with backoff at the pool level (PgBouncer handles
much of this), make the frontend distinguish a 5xx from a 4xx and show a real
error state instead of an infinite spinner, and add read replicas so analytics
outages do not take down writes.

**10. What happens during partial failure?**

The system is deliberately designed around this, and mostly gets it right:

| Failure | Behaviour |
|---|---|
| Websocket push fails | Swallowed and logged — the write succeeds |
| Email fails | Logged, retried 3× by Celery — the request succeeds |
| Broker unreachable | Task runs inline |
| Embedding fails | Recorded on the job row — the upload succeeded |
| LLM fails | 502, and the user's chat message is already persisted |

The gap is `HandoverViewSet.review`, which has no transaction around two related
writes.

**11. Which queries need better indexes?**

`projects_project(workspace, status, archived)` and
`documents_document(workspace, project)` are both filtered that way with no
composite index. Beyond that, every `?search=` produces leading-wildcard `ILIKE`
across `search_fields` — a full scan. `pg_trgm` GIN indexes or full-text search
would fix it, and the same applies to the RAG structured-context keyword matcher.

**12. Which APIs need better authorization?**

Honestly, few — tenancy is the strong part. Three notes:

- `resolve_workspace` leaks workspace existence via 404-vs-403.
- `pending_handovers` on the dashboard is workspace-wide, so a member sees a
  count of things they cannot act on. Cosmetic, but arguably an information leak.
- `GET /invitations/` returns the **token** to workspace admins. That is by
  design (they need it to resend), but the token is a bearer credential and it
  now lives in more places.

**13. What would you refactor first?**

Not a rewrite — three targeted changes:

1. Replace the three inline role checks with the existing unused permission
   classes, so `REVIEWER_ROLES` has one enforcement point.
2. Wrap `HandoverViewSet.review` in a transaction.
3. Generate `frontend/src/types/` from the OpenAPI schema instead of
   hand-mirroring the serializers.

**14. This is a monolith. When would you split it?**

Not yet, and I would resist it. The natural seam is `knowledge` + `ai` — they
have completely different dependency profiles (torch, ~90 MB models, provider
SDKs) and different scaling characteristics.

The trigger would be embedding load competing with web traffic for resources, or
needing GPU workers. Even then I would extract it as a **separate service behind
the same database** before considering separate data stores, because the tenancy
model would have to be replicated across the boundary.

**15. Is the signal-based architecture a good idea?**

It is a real trade and I would argue both sides.

For: one line adds auditing to a new model; domain apps stay unaware of
cross-cutting concerns; `apps/tasks/views.py` is 25 lines.

Against: it is implicit. Reading `TaskViewSet` gives no hint that saving a task
writes an audit row. Debugging requires knowing to look in `AppConfig.ready()`.
And it has a real blind spot — `queryset.update()` fires nothing.

At this size, the trade is worth it. At ten times the size I would want explicit
service functions for anything a reader needs to see.

**16. How would you add a second API version?**

The routing already anticipates it — `path("api/v1/", include((api_v1_patterns,
"v1"), namespace="v1"))`. A `v2` mounts alongside with its own URLConf and
serializers, sharing the models. The hard part is not routing, it is deciding how
long to support both and how to migrate the frontend, which currently has one
hard-coded `API_BASE_URL`.

**17. How do you handle schema migrations with zero downtime?**

The current setup does not: `web` runs `migrate` in its start command, so with N
replicas all N run it concurrently. Django takes an advisory lock so it is
usually safe, but the correct pattern is a separate migration job.

For zero downtime you also need expand-then-contract: add a nullable column,
deploy code that writes both, backfill, deploy code that reads the new one, then
drop the old. Nothing in this repo does that yet because there has been no
production deployment.

**18. What is your data-retention story?**

There isn't one, and several tables grow without bound:
`token_blacklist_outstandingtoken` (fastest — one row per refresh, and read on
every token validation), `activities_activity` (by design — it is an audit log),
`ai_searchhistory` (which stores raw query text, a privacy consideration),
`knowledge_embeddingjob`, and `notifications_notification`.

There is **no Celery beat schedule at all**, so even SimpleJWT's own
`flushexpiredtokens` never runs. That is the first thing I would add.

**19. If this had 10,000 workspaces and a million tasks, what breaks first?**

Query counts before storage. The dashboard's 15+ queries and the document list's
41 become the visible problem long before PostgreSQL struggles with a million
rows — those are small tables by database standards.

Then the analytics window scans, then the leading-wildcard `ILIKE` searches, then
vector search recall as the HNSW index grows (tunable with `ef_search`).

Storage-wise, `knowledge_documentchunk` grows fastest: a 50-page document is
roughly 300 chunks at 384 floats each.

**20. What are you proudest of, and what would you do differently?**

Proudest: **tenant isolation is structural.** One base class, four independent
enforcement points, and cross-tenant reads return 404 rather than 403 so the API
never confirms an id exists. Every domain viewset gets it for free, which means a
new feature is safe by default rather than safe if the author remembers.

Second: **everything degrades.** Redis, Celery, SMTP, the LLM and even pgvector
each have a documented fallback. Local development needs nothing but PostgreSQL,
which is a real onboarding win.

Differently: the token storage. Cookies-not-httpOnly was a deliberate trade for
the edge guard and I documented it in the file — but the right design has the
backend set an httpOnly refresh cookie with the access token in memory, which
also removes the reason the edge guard needed to read cookies at all. I would
also have added `completed_at` from the start rather than approximating in
analytics, and written the tenancy test first instead of last.

---

**Next:** [Difficult follow-ups](difficult-followups.md)
