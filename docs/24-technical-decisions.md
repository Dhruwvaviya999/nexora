# 24 — Technical Decisions

[← Back to index](README.md)

Each decision is labelled:

- ✅ **Confirmed** — the code or a code comment states the reason.
- 🔍 **Inferred** — no stated reason, but the code makes the rationale clear.
- ❓ **Unknown** — no evidence either way. Do not invent one.

This is the file to read before an interview asks *"why did you do it this way?"*

---

## 1. Stack choices

### Django + DRF rather than Node/Express ❓

**Unknown.** No comment, ADR or commit message explains the choice.

What you can say from the code — the features Django provides that this project
actively relies on: the ORM with migrations, `AbstractUser` and password hashing,
`default_token_generator` for reset links, the signals system (which four apps
depend on), the admin, `ContentType` for generic foreign keys, and DRF's
serializer/permission/throttle stack. Roughly half the codebase's structure comes
from those.

### Next.js App Router rather than Vite + React Router ❓

**Unknown.** But `src/proxy.ts` uses an edge feature that only exists in Next.js,
and route groups `(auth)` / `(app)` are used for exactly the thing they are for —
two layouts with no URL impact. So the choice is being used, not just present.

Counter-observation worth being honest about: **every `(app)` page is
`"use client"`**, so the app is not currently benefiting from server rendering of
data. The App Router is being used for routing and middleware, not for RSC data
fetching.

### PostgreSQL 🔍

**Inferred, and strongly.** pgvector requires PostgreSQL — there is no equivalent
in MySQL. `jsonb`, the `ArrayField`-free JSON usage, and the `HnswIndex` are all
PostgreSQL-specific. The requirement is stated in `requirements.txt`: pgvector is
"the Python client only — the pgvector *server extension* must be installed into
PostgreSQL separately."

### pgvector rather than a dedicated vector database ✅

`backend/apps/knowledge/models.py` and the README both frame it as keeping
embeddings in the same database. The practical argument, visible in the code: the
tenant filter and the vector search happen in **one query** —

```python
DocumentChunk.objects.filter(workspace=workspace, embedding__isnull=False)
    .annotate(distance=CosineDistance("embedding", query_vector))
```

With Pinecone or Weaviate you would either replicate the tenancy model into the
vector store or filter after retrieval. One database also means one backup, one
transaction boundary, and no sync job.

### Native `fetch` rather than Axios 🔍

**Inferred.** No comment states it, but the consequences are visible:
`lib/api/client.ts` is 142 lines and implements exactly what this app needs —
JWT injection, single-flight refresh, FormData handling, error normalisation.
Axios would supply interceptors but the refresh logic would still have to be
written, so the dependency buys little.

Defensible answer: *"The wrapper is small and the behaviour I needed —
single-flight refresh with a one-shot retry — is custom anyway. Adding Axios
would add a dependency without removing code."*

### TanStack Query rather than Redux 🔍

**Inferred, and the code supports it decisively.** There is almost no shared
mutable *client* state in this app — it is nearly all server state. Server state
in a Redux store means duplicating the database and writing code to keep the
duplicate correct. TanStack Query treats it as a cache with invalidation rules,
which is what it is.

The two genuinely client-owned pieces — "who am I" and "which workspace" — are
exactly the two React Contexts that exist.

### shadcn/ui rather than MUI/Chakra 🔍

**Inferred from `components.json` and the 29 files in `components/ui/`.** shadcn
copies source into your repo rather than installing a package, so components are
editable and there is no theme-override fight. Confirmed by the fact that some of
them *have* been edited (e.g. `Button` has an `xs` size used in
`notification-bell.tsx:53` which is not in the shadcn default).

---

## 2. Architecture decisions

### Workspace as the tenant boundary, on every table ✅

`apps/common/models.py:70-75`: *"Every domain object hangs off a workspace (the
tenant boundary)."*

Alternative approaches — schema-per-tenant, database-per-tenant — cost far more
operationally. A `workspace_id` column plus one base queryset filter gives
isolation with a single point of enforcement.

The cost is that **the filter must never be forgotten**. That is exactly why
`WorkspaceScopedViewSet` exists: it makes the safe path the default.

### `WorkspaceScopedViewSet` ✅

`apps/common/viewsets.py:3-7`: *"Projects, tasks, and documents all share the
same access pattern... This base centralises that logic so each module only
declares its serializer, filterset, and search/ordering fields."*

Result: `apps/tasks/views.py` is 25 lines.

### Cross-tenant access returns 404, not 403 🔍

**Inferred but clearly deliberate** — it is a direct consequence of filtering the
queryset rather than checking permission on a fetched object. 403 would confirm
that the id exists somewhere. 404 does not.

### Signals for cross-cutting concerns ✅

`apps/activities/handlers.py:1-7`: *"Domain apps stay untouched — adding history
is just registering a model here."*
`apps/activities/models.py:4-6`: *"Rows are written by signal handlers (never by
hand at call sites)."*

**The honest counter-argument** (worth raising yourself in an interview): signals
are implicit. A reader of `apps/tasks/views.py` has no way to see that saving a
task writes an audit row. And any write that bypasses `post_save` —
`queryset.update()`, `bulk_create`, raw SQL — is silently unaudited.

The trade was made consciously, and the alternative (explicit service calls at
every call site) would have put audit logging in ~15 places.

### Services layer only where there is real logic 🔍

There is no `services.py` for projects or tasks — those are CRUD, and a service
layer would be a pass-through. Services exist exactly where logic does:
`activities/services.py`, `notifications/services.py`, `mentions/services.py`,
`knowledge/services/*`, `ai/services/*`.

Defensible: *"I added a service layer where there was logic to hold, not as a
uniform rule."*

### One image for web and worker ✅

`docker-compose.yml:10-11`: *"The web and worker services run the same image;
only the command differs, so they cannot drift apart."*

### uvicorn directly, not gunicorn ✅

`backend/Dockerfile:50-52`: *"An ASGI server is required for the websocket
routes, and uvicorn manages its own worker processes. gunicorn's uvicorn.workers
shim is deprecated upstream, so it is deliberately not used."*

`gunicorn` remains in `requirements.txt` and is unused by any command in the repo.

---

## 3. Authentication decisions

### JWT rather than server sessions 🔍

**Inferred.** The consequences the code relies on: the API is stateless, so
`web` can scale horizontally with no sticky sessions or shared session store; and
a cross-origin SPA cannot easily use session cookies without CSRF plumbing.

The cost is acknowledged in the code: revocation needs the blacklist tables.

### Rotation + blacklist ✅ (configuration is explicit)

```python
"ROTATE_REFRESH_TOKENS": True,
"BLACKLIST_AFTER_ROTATION": True,
```

Makes a refresh token single-use. If it is stolen and used, the legitimate user's
next refresh fails — turning silent compromise into a visible session death.

### Cookies rather than localStorage ✅

**Superseded.** The original design put both tokens in non-httpOnly cookies so
`proxy.ts` could read them, and documented the trade-off in the file.

That has since been changed: the backend issues the refresh token as an
**httpOnly** cookie, the access token is held in memory, and `proxy.ts` reads
`nexora.session` — a marker containing `"1"` and no credential. The original
reasoning was sound (the edge guard genuinely needed *something* readable), but
the marker satisfies that need without exposing a token.

The lesson worth keeping: the constraint was "the edge needs to know whether a
session exists", not "the edge needs the token". Restating the requirement
removed the trade-off entirely. See [18-security.md](18-security.md).

### Login returns the user object with the tokens 🔍

`EmailTokenObtainPairSerializer` adds five lines to save a `/auth/me/` round trip
on every login. The docstring notes it "only enriches the response" — the parent
still does credential validation.

### The edge guard checks presence, not validity ✅

`frontend/src/proxy.ts:8-11`: *"It only checks presence, not validity — the API
client handles expiry via silent refresh, and the protected layout redirects if
the session is truly dead. This keeps the guard fast and avoids verifying JWTs
here."*

### Password reset revokes every session ✅

`accounts/views.py:166-168`: *"Refresh tokens outlive the reset by days, so
anyone holding one (including whoever prompted the reset) keeps access unless
they are revoked."*

### The reset endpoint does not reveal whether an account exists ✅

`accounts/views.py:110-113`: *"Saying 'no such user' here would turn this
endpoint into a way to test which email addresses are registered."*

### Credential throttles key on IP, not user ✅

`common/throttling.py:7-9`: an attacker with no valid account *"would otherwise
get a fresh bucket for every email address they guess."*
And `throttling.py:29-32`: keying password reset by the submitted email *"would
let an attacker lock a specific person out of resets."*

---

## 4. Data modelling decisions

### UUID primary keys ✅

`apps/common/models.py:27`: *"Uses a non-sequential UUID primary key (safe to
expose in URLs/APIs)."*

### `related_name="+"` on audit FKs ✅

`apps/common/models.py:45-47`: *"disables the reverse accessors so many models
can share these FKs without clashing on the user model."*

### `related_name="%(class)ss"` on workspace ✅

`apps/common/models.py:72-74`: gives `workspace.projects`, `workspace.tasks`,
`workspace.documents` automatically.

### Generic foreign keys for comments and activity ✅

`apps/comments/models.py:4-6`: *"One reusable comment table serves every
commentable resource (projects, tasks, documents, and anything added later)."*

The cost — no database-level referential integrity on `object_id` — is bounded on
the comment side by the `ALLOWED_TARGETS` whitelist.

### `object_id` is a UUID, not an integer ✅

`apps/comments/models.py:38-39`: *"object_id is a UUID because every domain model
uses a UUID primary key."*

### Soft delete for comments only ✅

`apps/comments/models.py:6`: *"deletes are soft so reply chains stay intact."*
Nothing else needs it, so nothing else has it.

### `workspace_id` denormalised onto `DocumentChunk` ✅

`apps/knowledge/models.py:8-10`: *"so the tenant boundary can be enforced with a
single indexed filter on similarity queries — the hot path for semantic search."*

### `workspace_id` denormalised onto `Mention` ✅

`apps/mentions/models.py:26`: *"for cheap 'my mentions in workspace X' reads."*

### Notification `title` and `link` denormalised at write time 🔍

**Inferred.** A notification is a record of what was true when it happened, not a
live view. It also means rendering the feed needs no joins.

### No `completed_at` on Task ❓

**Unknown whether this was a decision or an oversight.** What *is* confirmed is
that the consequence was noticed: `AnalyticsView`'s docstring says *"'Completed'
per week counts tasks whose status is completed by their last update in that week
(the model has no dedicated completed_at column)."*

Documented approximation rather than a hidden bug — but it should be added.

---

## 5. AI decisions

### `knowledge` and `ai` as separate apps 🔍

Retrieval and generation are separable concerns with different dependencies
(torch versus provider SDKs) and different failure modes. `ai` imports
`knowledge`; `knowledge` never imports `ai`. That one-way edge is the design.

### Provider abstraction ✅

`apps/ai/providers/base.py:3-6`: *"The rest of the app (RAG, summarizer, action
items) talks only to this interface, so the underlying model can be swapped
per-workspace without touching business logic."*

### Lazy SDK imports ✅

Same file: *"Concrete providers import their SDKs lazily."* A missing package
becomes a clean `ProviderError`, not an import-time crash for everyone.

### Per-workspace API keys, encrypted ✅

`apps/ai/services/crypto.py:1-8` documents the whole scheme including the
production warning about deriving the key from `SECRET_KEY`.

### Word-window chunking rather than a tokenizer ✅

`apps/knowledge/services/chunker.py:6-8`: *"deliberately dependency-free and
deterministic; a token-accurate splitter (tiktoken / model tokenizer) can replace
this later without changing the interface."*

### Local embeddings rather than an API ✅ (implied by the code and comments)

`sentence_transformer.py`: no network, no API key. Free, private, and offline —
at the cost of a 90 MB model per worker process, which is why
`CELERY_WORKER_PREFETCH_MULTIPLIER = 1` and `--concurrency=2`.

### HNSW rather than IVFFlat 🔍

**Inferred, and correct.** Documents arrive one at a time; IVFFlat needs a
training pass and degrades as new rows accumulate. HNSW is incremental.

### AI-suggested tasks are not persisted ✅

`apps/ai/services/action_items.py:5-7`: *"The tasks are NOT persisted here —
they're returned for the user to review and approve, after which the frontend
creates them through the existing Task API."*

This is the strongest AI-safety decision in the codebase: the LLM never writes to
the database, and every created task passes the same validation as a manual one.

### Retrieved content is treated as untrusted ✅

`apps/ai/services/security.py:1-12` names the three trust levels explicitly.

---

## 6. Realtime decisions

### The socket is push-only ✅

`apps/notifications/consumers.py:8-9`: *"Marking things read still goes through
the REST API, which keeps one code path for permissions and auditing."*

### The socket carries a signal, not data ✅

`hooks/use-notification-socket.ts:25-29`: *"The socket only signals that
something changed; the data still comes from the REST API via an invalidation, so
there is one source of truth and no chance of the cache drifting from what the
server would return."*

### Polling as a fallback ✅

Same file: *"When it is not [live] — no websocket support, a proxy that strips
upgrades, the server running under plain WSGI — callers keep polling instead, so
the feature degrades rather than disappears."*

### Realtime failure must never break a write ✅

`consumers.py:69-73` and `notifications/services.py:56-61`.

### Origin validated against `CORS_ALLOWED_ORIGINS`, not `ALLOWED_HOSTS` ✅

`config/asgi.py:37-41`: the Origin is the *frontend's*, `ALLOWED_HOSTS` lists the
*API's* hostnames — *"split them across api.example.com and app.example.com and
every socket would be denied."*

### Token in the query string ✅

`common/channels_auth.py:4-8`: the browser WebSocket API cannot set headers. The
mitigations — wss in production, 15-minute token lifetime — are stated.

---

## 7. Operational decisions

### Development requires nothing but PostgreSQL ✅

`config/settings/development.py:26-29`: *"Nexora runs locally with nothing but
Postgres. Redis, a Celery worker and an SMTP server are all optional here; each
falls back to an in-process equivalent, and every one of them is switched on by
simply setting the matching environment variable."*

This is the best operational decision in the project. Onboarding cost is one
database.

### Throttling off in tests ✅

`config/settings/test.py:44-50`, including the subtlety that clearing
`DEFAULT_THROTTLE_CLASSES` is not enough because the auth views name their
throttles explicitly — a rate of `None` is what actually disables a scope.

### MD5 password hasher in tests ✅

`test.py:66-69`: *"The default PBKDF2 hasher is deliberately slow; the suite
creates a lot of users and does not test hashing strength."*

### Queue after commit, never before ✅

Stated twice, in `knowledge/services/processor.py:54-56` and
`common/email.py:79-85`.

### Fall back to inline when the broker is down ✅

`processor.py:47-48`: *"broker down: better slow than lost."*

### A dedicated plain-text template engine ✅

`config/settings/base.py:117-127` — the `&` → `&amp;` bug in reset links,
explained in full, including why the engine must come *after* the default one.

### Docker images build only on push, not PR ✅

`.github/workflows/ci.yml:124-125`: *"building the backend image pulls torch, so
it is too slow to run on every pull request."*

### `makemigrations --check` in CI 🔍

Makes it impossible to merge a model change whose migration was forgotten. The
most valuable single CI step in the pipeline.

---

## 8. Decisions worth revisiting

Honest self-assessment. Saying these unprompted in an interview is stronger than
being caught by them.

| Decision | Why revisit |
|---|---|
| Non-httpOnly token cookies | The XSS blast radius is both tokens. The fix removes the need for `proxy.ts` to read them at all |
| No `completed_at` on Task | The analytics approximation is documented but wrong in a way users would notice |
| `Comment.author` on `CASCADE` | Inconsistent with every other user FK, which is `SET_NULL`. Deleting a user erases other people's reply threads |
| `Workspace.owner` on `CASCADE` | Deleting one user can destroy an entire workspace |
| Every `(app)` page is `"use client"` | Gives up the App Router's main advantage. A server-rendered shell would cut the three sequential startup round trips |
| Filter state in `useState`, not the URL | Filtered views cannot be shared or bookmarked |
| No `CONN_MAX_AGE` | One line, immediate win |
| `IsWorkspaceAdmin` / `IsWorkspaceManager` defined but unused | The same logic is written inline in three places |
| ~~No error boundary~~ | ✅ Fixed — three boundaries added |

---

**Next:** [25 — Known Limitations](25-known-limitations.md)
