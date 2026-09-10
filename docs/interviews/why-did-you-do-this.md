# Interview — "Why Did You Do It This Way?"

[← Interviews index](README.md) · [Full decision log](../24-technical-decisions.md)

Every answer here follows the same shape: **what I did → why → what it cost →
when I would choose differently.** That last part is what separates a good answer
from a defensive one.

---

## Stack

### "Why Django and not Node/Express?"

> Half this system's structure comes from things Django gave me: the ORM with
> migrations, `AbstractUser` with password hashing, `default_token_generator` for
> reset links that self-invalidate, the signals system that four apps depend on,
> `ContentType` for generic relations, and DRF's serializer/permission/throttle
> stack. Rebuilding those in Express would have been most of the project.
>
> The cost is that Python is slower per request than Node, and the async story is
> more awkward — I had to use Channels and ASGI explicitly for websockets.
>
> If the product were realtime-first rather than CRUD-with-realtime, I would
> reconsider.

### "Why Next.js and not plain React?"

> Two things I actually use: an edge route guard that runs before a page renders,
> which client-side routing cannot do, and route groups so `(auth)` and `(app)`
> get different layouts with no URL impact.
>
> The honest caveat is that every authenticated page is `"use client"`, so I am
> not currently benefiting from server components for data — I use the App Router
> for routing and middleware, not RSC fetching. That is the main thing I would
> revisit; a server-rendered shell would remove the three sequential round trips
> on startup.

### "Why PostgreSQL?"

> pgvector, primarily. There is no equivalent in MySQL, and the entire RAG feature
> depends on 384-dimension vectors with an HNSW index living in the same database
> as everything else. `jsonb` and Django's PostgreSQL support are secondary.

### "Why pgvector and not Pinecone or Weaviate?"

> Because the tenant filter and the vector search become **one query**. With a
> separate store I would have to replicate the tenancy model into it, or filter
> after retrieval — and get the isolation right twice. One database also means one
> backup and one transaction boundary.
>
> The cost is that I inherit PostgreSQL's scaling characteristics for vector
> search. At hundreds of millions of vectors a dedicated store wins.

### "Why no Axios?"

> The behaviour I needed — single-flight refresh with a one-shot retry — is custom
> either way. Axios gives me interceptors, but I would still write that logic. The
> wrapper is 142 lines and handles JWT injection, refresh, FormData detection and
> error normalisation. Adding the dependency would not have removed code.

### "Why TanStack Query and not Redux?"

> Because almost nothing here is shared mutable *client* state — it is nearly all
> server state. Putting server state in Redux means duplicating the database and
> writing code to keep the duplicate correct. TanStack Query treats it as a cache
> with invalidation rules, which is what it actually is.
>
> The two things that genuinely are client-owned — who am I, and which workspace
> am I in — are exactly the two React Contexts that exist.

---

## Architecture

### "Why workspace-per-row rather than schema-per-tenant?"

> A `workspace_id` column with one queryset filter is dramatically cheaper
> operationally — one database, one migration run, one connection pool. Schema-
> or database-per-tenant means N migrations and N connections.
>
> The cost is that the filter must never be forgotten. That is precisely why
> `WorkspaceScopedViewSet` exists: it makes the safe path the default, so a new
> endpoint is isolated unless someone deliberately opts out.
>
> If a customer demanded physical data separation, I would price a dedicated
> deployment rather than retrofit a database router — routers would have to be
> threaded through every query and the membership join would break.

### "Why signals for the audit log?"

> Adding history for a new model is one line in `activities/handlers.py`, and no
> domain app imports the activities app at all — `apps/tasks/views.py` is 25 lines
> and knows nothing about auditing.
>
> The cost is real and I would raise it myself: signals are implicit, so reading
> the view gives no hint that saving writes an audit row. And there is a blind
> spot — `queryset.update()`, `bulk_create` and raw SQL fire nothing.
>
> At this size the trade is worth it. At ten times the size I would want explicit
> service functions for anything a reader needs to see.

### "Why is `apps/tasks/views.py` only 25 lines? Where's the logic?"

> Distributed deliberately. Tenancy and audit stamping are in
> `WorkspaceScopedViewSet`. Validation and the workspace derivation are in the
> serializer. Query params are in the FilterSet. Audit logging is a signal. What is
> left in the view is genuinely view-specific: which serializer, which filters,
> which fields are searchable.

### "Why not a service layer for every app?"

> Because for projects and tasks it would be a pass-through with no logic in it.
> Service modules exist exactly where there is logic to hold — activities,
> notifications, mentions, the knowledge pipeline, the AI services. Adding empty
> layers for symmetry costs indirection and buys nothing.

---

## Authentication

### "Why JWT and not sessions?"

> The API is stateless, so the web tier scales horizontally with no sticky
> sessions or shared session store. And a cross-origin SPA cannot easily use
> session cookies without CSRF plumbing.
>
> The cost is revocation — which is why `ROTATE_REFRESH_TOKENS` and
> `BLACKLIST_AFTER_ROTATION` are on, and why the blacklist tables exist. That
> makes a refresh token single-use, so a stolen one causes a visible session death
> rather than silent parallel access.

### "Why are the tokens in cookies and not localStorage?"

> So `src/proxy.ts` — the Next.js edge guard — can read them server-side. That is
> the only reason.
>
> The cost is that they cannot be httpOnly, because the client sets them. So any
> XSS on the frontend origin would expose both, and the refresh token is valid for
> seven days. I documented that trade-off in the file itself rather than leaving it
> implicit.
>
> The correct design is a backend-set httpOnly refresh cookie with the access token
> in memory — which also removes the reason the edge guard needed to read cookies
> at all. That is the first thing I would change.

### "Why does the edge guard only check that a cookie exists?"

> Verifying a JWT at the edge on every navigation is slow, and it would duplicate
> logic that already exists. The API client handles expiry via silent refresh, and
> the protected layout redirects if the session is truly dead. The guard's job is
> to avoid rendering a page for someone obviously logged out — it is UX, not
> security.

### "Why 15 minutes and 7 days?"

> Fifteen minutes bounds the damage from a stolen access token while being long
> enough that refresh is rare. Seven days is how long a session survives without
> re-login, and it is short enough that an abandoned token expires. Both are
> environment variables, so they are tunable per deployment.

---

## Data modelling

### "Why UUID primary keys?"

> Safe to expose in URLs and APIs with no enumeration, generated before insert,
> and collision-free across environments.
>
> Costs: 16 bytes versus 4, and random values hurt B-tree locality on insert.
> That is why everything orders by `-created_at` rather than by id.

### "Why generic foreign keys for comments?"

> One comment table serves projects, tasks and documents, and anything added
> later. The alternative — `ProjectComment`, `TaskComment`, `DocumentComment` — is
> three tables, three serializers and three viewsets that are identical.
>
> The cost is no database-level referential integrity on `object_id`. I bounded
> that on the comment side with an `ALLOWED_TARGETS` whitelist, so `target_type`
> can only name three known models.

### "Why is `workspace` read-only on `TaskSerializer`?"

> Because it is derived from the project. If a client could send it, they could
> post a project from tenant A while claiming workspace B — which would poison
> every scoped query, since those filter on `workspace_id`. Deriving it makes the
> mismatch impossible rather than merely validated against.

### "Why soft-delete comments but nothing else?"

> Because comments thread. Hard-deleting a parent takes its replies with it, which
> destroys other people's content. Nothing else in the schema has that property,
> so nothing else needs the complexity.
>
> Note the delete genuinely blanks the content rather than just hiding it, so a
> serializer that forgot the `[deleted]` override still could not leak it.

---

## AI

### "Why local embeddings instead of an API?"

> Free, private and offline — no key required, and workspace documents never leave
> the deployment for the embedding step.
>
> The cost is a ~90 MB model held in memory per worker process, which is why
> compose caps `--concurrency=2`, and a slow first run while it downloads. The
> Dockerfile installs the CPU-only torch wheel first specifically to avoid pulling
> gigabytes of CUDA runtime a CPU worker never uses.

### "Why 220-word chunks with 40-word overlap?"

> The overlap is the interesting part: a sentence that straddles a chunk boundary
> would otherwise be retrievable from neither side. Forty words on 220 is about
> 18% redundancy — 18% more vectors for materially better boundary recall.
>
> It is deliberately dependency-free and deterministic; a token-accurate splitter
> can replace it without changing the interface, which matters because there are
> three swappable LLM providers with different tokenizers.

### "Why aren't AI-generated tasks saved automatically?"

> Because the model would then be writing to the database. Suggestions are
> returned for human review and created through the normal Task API, so they pass
> the same validation as a manual task — and a hallucinated task cannot silently
> appear in someone's list.
>
> It is also why I keep `_VALID_PRIORITIES` identical to `TaskPriority`: approved
> suggestions have to be accepted by the existing endpoint.

### "How seriously do you take prompt injection?"

> Seriously enough to build three layers — sanitisation, fencing retrieved content
> as untrusted, and explicit guardrails stating that CONTEXT is data and never
> instructions — and honestly enough to say those are not a guarantee. Prompt
> injection is not solved.
>
> The real containment is architectural: retrieval is workspace-scoped, so an
> injection cannot reach another tenant, and the model has no tools, so it cannot
> write anything.

---

## Realtime

### "Why is the websocket push-only?"

> So there is one code path for permissions and auditing. Marking a notification
> read goes through REST, where the permission check and any future audit already
> live. Adding a second write path through the socket would mean duplicating both.

### "Why does the socket carry no data the client trusts?"

> Because the list is paginated and filtered server-side. If the client rendered
> the pushed payload directly, its cache could drift from what the server would
> actually return. Treating the message as "something changed — refetch" keeps one
> source of truth.
>
> It costs an extra round trip per notification, which is cheap.

### "Why polling as well?"

> Because websockets fail in the real world — proxies strip upgrades, the server
> might run under plain WSGI, some networks block them. `refetchInterval: isLive ?
> false : 30_000` means a live client makes zero periodic requests and a
> socket-less client still works. The feature degrades rather than disappearing.

---

## Operations

### "Why does development need nothing but PostgreSQL?"

> Because onboarding cost is a real cost. Redis, Celery and SMTP each fall back to
> an in-process equivalent in the development settings, and each is switched on by
> setting one environment variable. Someone can clone this repo and have it running
> with one database.
>
> The trap I had to avoid is those fallbacks being wrong in production — the
> in-memory channel layer is per-process, and the LocMem throttle cache makes
> limits `rate × worker_count`. Both are called out in comments.

### "Why is throttling disabled in tests?"

> A test that walks 40 endpoints is not an attack. The subtle part is that
> clearing `DEFAULT_THROTTLE_CLASSES` is not enough — the auth views name their
> throttles explicitly, which overrides the default. Setting each **rate** to
> `None` is what actually disables a scope.

### "Why uvicorn rather than gunicorn?"

> An ASGI server is required for the websocket routes, uvicorn manages its own
> worker processes, and gunicorn's `uvicorn.workers` shim is deprecated upstream.
> Gunicorn is still in requirements and unused — I would remove it.

---

## The universal fallback

If you genuinely do not know why something is the way it is:

> "I don't have a documented reason for that one. Looking at it now, the effect
> is X, and the trade-off is Y. If I were choosing again I'd probably Z — but I
> won't invent a rationale after the fact."

That is a **better** answer than a confident guess. Interviewers can tell the
difference, and inventing a reason is the one thing that reliably costs you
credibility.

---

**Next:** [Difficult follow-ups](difficult-followups.md)
