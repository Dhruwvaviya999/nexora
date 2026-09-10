# Interview — "Tell Me About Your Project"

[← Interviews index](README.md)

Four versions. Learn the 30-second one word for word; the rest should feel
conversational, not recited.

---

## 30 seconds

> Nexora is a multi-tenant team workspace — projects, tasks and documents, built
> with Django REST Framework and Next.js on PostgreSQL.
>
> The two things that make it more than a task tracker are **formal task
> handovers** — you hand work to a teammate with a written summary and a manager
> approves it before the assignment actually changes — and an **AI assistant**
> that answers questions over the team's own documents using vector search in
> PostgreSQL with pgvector.
>
> The organising principle is that every object belongs to a workspace, and one
> base class enforces that on every query.

---

## 1 minute

> Nexora is a multi-tenant team workspace. Each company is a *workspace*, people
> join it with a role — owner, admin, manager or member — and everything inside
> is projects, tasks and documents.
>
> Two features go beyond ordinary CRUD.
>
> The first is **task handovers**. Normally reassigning a task is one click and
> all the context is lost. Here the outgoing person writes a work summary,
> pending items and resources; a manager reviews it; and only on approval does
> the task's assignee actually change. Every handover exports as a PDF.
>
> The second is an **AI assistant**. Uploaded documents are parsed, chunked and
> embedded into a pgvector column, and questions run a cosine-similarity search
> scoped to that workspace before the results go into the prompt. So answers come
> with citations and a confidence score, grounded in the team's own data.
>
> Backend is Django 5 and DRF; frontend is Next.js 16 with TanStack Query.
> Realtime notifications go over Django Channels with a polling fallback, and
> document embedding runs on a Celery worker. The whole thing runs in Docker
> compose, and CI runs the test suite against real Postgres and Redis.
>
> The design principle throughout is that **every object hangs off a workspace**,
> and a single base viewset enforces that on every query — so tenant isolation is
> structural rather than something each endpoint has to remember.

---

## 3 minutes

> **The problem.** Three things, really.
>
> Work changes hands and context disappears. Team knowledge lives in documents
> nobody re-reads. And nobody can reconstruct who changed what. Nexora addresses
> all three in one workspace.
>
> **The shape.** Next.js 16 frontend, Django 5 + DRF backend, PostgreSQL with
> pgvector, Redis for background jobs and websockets. A request goes: page →
> TanStack Query hook → a typed API layer → a fetch wrapper that attaches the
> JWT → Django URL routing → a DRF ViewSet → permission check → serializer →
> ORM → PostgreSQL, and back.
>
> **Multi-tenancy** is the core idea. Almost every table has a `workspace_id`,
> and there's a base class — `WorkspaceScopedViewSet` — whose `get_queryset`
> filters through the membership table. So a request for another tenant's task
> returns **404, not 403**, because the row was never in the queryset. That means
> the API never even confirms the id exists. Each domain viewset is then about
> fifteen lines — the tenancy, the audit stamping and the permission checks are
> all inherited.
>
> **Auth** is JWT: a 15-minute access token and a 7-day refresh token that
> rotates and blacklists the old one on every use. The frontend keeps them in
> cookies so the Next.js edge middleware can gate routes, and my API client does
> a single-flight refresh — if ten requests get a 401 at once, exactly one
> refresh fires and they all wait on it. That matters because rotation makes the
> refresh token single-use, so parallel refreshes would invalidate each other.
>
> **The handover workflow** is the richest business logic. A member submits with
> a summary; only owners, admins and managers can review; rejection requires a
> written comment; approval is the only place in the whole codebase where one
> module writes to another's table — it sets `task.assignee`. It's also the only
> capability that distinguishes a manager from a member.
>
> **The AI side** is genuinely two layers. Ingestion: upload triggers a Django
> signal that queues a Celery job, which extracts text from PDF or DOCX, splits
> it into 220-word overlapping windows, embeds each with a local
> sentence-transformers model, and stores 384-dimension vectors with an HNSW
> index. Retrieval and generation: a question gets embedded, cosine-searched
> **within the workspace**, and the top six chunks go into a prompt alongside a
> live snapshot of the projects and tasks. Retrieved content is explicitly fenced
> as untrusted, with guardrails telling the model that document content is data
> and never instructions.
>
> **Cross-cutting concerns are decoupled with signals.** The audit log is written
> entirely by `post_save` and `post_delete` receivers — no domain app imports the
> activities app at all, so adding history for a new model is one line. Same for
> mentions and for kicking off embedding.
>
> **What I'd change.** The tokens aren't httpOnly — that was a deliberate
> trade-off to let the edge middleware read them, and it's documented in the
> file, but the right fix is a backend-set httpOnly refresh cookie with the
> access token in memory. There's no `completed_at` column, so the analytics
> chart infers completion week from `updated_at` — I noted that in the view's
> docstring rather than hiding it. And the document list has an N+1 I'd fix with
> an annotate and a prefetch.

---

## 5 minutes — the deep dive

Use the 3-minute version as the spine, then add these four blocks as the
conversation invites them.

### Block A — the request path, precisely

> Take creating a task. The form is react-hook-form with a zod schema that
> mirrors the backend rules. On submit it calls a TanStack Query mutation, which
> calls a typed function in my API layer, which calls a fetch wrapper — no Axios,
> it's about 140 lines and does JWT injection, single-flight refresh, FormData
> detection and error normalisation.
>
> On the backend, DRF routes to `TaskViewSet`, which is 25 lines. The serializer
> does the real work: it derives `workspace` from the project rather than trusting
> the client — that field is read-only — and it validates that the assignee is
> actually a member of that workspace. Then the base viewset checks membership
> and stamps `created_by`/`updated_by`, and a `post_save` signal writes the audit
> row. Response comes back, the mutation invalidates the `["tasks"]` query key,
> and every list re-renders.
>
> That `workspace` derivation matters: without it a client could post a project
> from tenant A while claiming tenant B, and poison every scoped query.

### Block B — the async pipeline

> Uploading a document returns immediately. A `post_save` signal on `Document`
> checks the extension, creates an `EmbeddingJob` row, and queues a Celery task —
> but deferred with `transaction.on_commit`, because queueing before the commit
> races the worker: it could read a row that isn't visible yet, or act on a
> transaction that rolled back.
>
> If the broker is unreachable, it catches that and runs the job inline —
> "better slow than lost." The worker records failures on the job row rather than
> raising, so the UI can show a status badge. And re-indexing deletes and
> bulk-inserts chunks inside one transaction, so a document is never left with
> zero chunks mid-reindex.
>
> The same `on_commit` pattern is used for outgoing email and for websocket
> pushes, for the same ordering reason.

### Block C — realtime, and degrading gracefully

> Notifications push over a websocket. Channels routes `/ws/` separately from
> HTTP in the ASGI application, behind an origin validator and JWT middleware
> that reads the token from the query string — the browser WebSocket API can't
> set headers.
>
> The interesting part is what the socket carries: **nothing the UI trusts.** It
> just signals "something changed", and the client invalidates the React Query
> cache and refetches over REST. One source of truth, no chance of the cache
> drifting from what the server would return. And when the socket isn't
> connected, the unread count polls every 30 seconds instead — so it degrades
> rather than disappearing.
>
> That pattern runs through the whole system. Redis down means an in-process
> channel layer and inline tasks. LLM down means a 502 with the provider's
> message. pgvector missing means a clean 503 with setup instructions instead of
> a leaked 500. PostgreSQL is the only hard dependency, and local development
> needs nothing but Postgres.

### Block D — what I'd do next

> Four things, in order.
>
> Move the refresh token into an httpOnly cookie set by the backend. That closes
> the XSS exposure and removes the reason the edge middleware needed to read
> cookies at all.
>
> Set `CONN_MAX_AGE` — right now every request opens a new PostgreSQL connection,
> which is one line to fix and the first thing that would break under load.
>
> Fix the N+1s: the document serializer's two `SerializerMethodField`s hit the
> database per row, and three other serializers use `source="...count"`.
>
> And write the missing tests. I covered the risky parts — password reset, the
> role matrix, the handover workflow, websocket isolation — but `tasks` and
> `projects` have empty test files, and the frontend's most logic-dense file, the
> API client with the refresh logic, has no test at all. That's the gap I'd close
> first.

---

## Delivery notes

**Do**
- Say file and class names. `WorkspaceScopedViewSet`, `EmailTokenObtainPairSerializer`,
  `create_notification`. It proves you wrote it.
- Volunteer one trade-off unprompted, early. It reframes everything after it.
- Use "I" — you built this.
- Stop and let them steer. The 3-minute version should end with a natural pause.

**Don't**
- List the tech stack as a feature. Anyone can install packages.
- Say "it's a simple CRUD app". It isn't — there's a vector pipeline, a review
  workflow, signal-driven auditing and realtime in there.
- Claim things the code does not do: there is no OCR, no email verification, no
  streaming AI responses in use, no production media serving, no scheduler.
- Get defensive about a weakness. Agree, explain the trade, give the fix.

**The single best sentence you can say:**

> "Every object hangs off a workspace, and one base class enforces that on every
> query — so tenant isolation is structural rather than something each endpoint
> has to remember."

It shows you think in invariants, not features.
