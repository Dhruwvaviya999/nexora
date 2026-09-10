# Interview — The Architecture Whiteboard

[← Interviews index](README.md)

How to draw this system live, in the right order, without stalling.

---

## The golden rule

**Draw the happy path first. Add the side channels only when asked.**

Nothing kills a whiteboard explanation faster than drawing Celery, Redis and
websockets before the interviewer knows what the product does.

---

## Step 1 — The spine (30 seconds)

Say: *"Let me start with the main request path."*

```
   Browser
      │
      ▼
   Next.js  :3000
      │   fetch + Bearer JWT
      ▼
   Django + DRF  :8000
      │
      ▼
   PostgreSQL + pgvector
```

Then: *"Everything else hangs off this."*

---

## Step 2 — Expand each side (1 minute)

```
┌──────────────── Browser ─────────────────┐
│  page.tsx                                │
│      ↓                                   │
│  hooks/use-*.ts   (TanStack Query cache) │
│      ↓                                   │
│  lib/api/*.ts     (typed endpoints)      │
│      ↓                                   │
│  lib/api/client.ts  ← JWT + refresh      │
└────────────────┬─────────────────────────┘
                 │  HTTPS, Authorization: Bearer
┌────────────────▼─────────────────────────┐
│  config/urls.py     /api/v1/*            │
│      ↓                                   │
│  ViewSet            (controller)         │
│      ↓                                   │
│  Permission         ← workspace role     │
│      ↓                                   │
│  Serializer         (validate / shape)   │
│      ↓                                   │
│  Model / ORM                             │
└────────────────┬─────────────────────────┘
                 ▼
           PostgreSQL
```

Say while drawing: *"Four layers each side, and each has exactly one job. The
client layer is where JWT and token refresh live; the permission layer is where
the workspace role is checked."*

---

## Step 3 — The tenancy box (the most important thing you draw)

Draw a box **around** the ViewSet and label it:

```
      ┌───────────────────────────────────────────┐
      │  WorkspaceScopedViewSet                   │
      │                                           │
      │  get_queryset():                          │
      │    .filter(workspace__members__user=me)   │
      │                                           │
      │  → another tenant's row is never in       │
      │    the queryset → 404, not 403            │
      └───────────────────────────────────────────┘
```

Say: *"This is the single most important class in the system. Every scoped
resource inherits it, so tenant isolation is structural rather than something each
endpoint has to remember."*

**If you draw only one thing well, draw this.**

---

## Step 4 — Where auth sits

Add three markers to the diagram you already have:

```
  Browser ──1──► proxy.ts (edge)      cookie present? → redirect
              │
              ├──2──► app/(app)/layout.tsx    useAuth() → redirect
              │
              └──3──► DRF permissions          ← THE ONLY REAL BOUNDARY
```

Say: *"Three layers, but only the third is security. The first two are UX — they
stop you rendering a page you can't use."*

Then the token loop, drawn small in a corner:

```
  request ──► 401 ──► POST /auth/refresh/ ──► retry once
                          (single-flight)
```

---

## Step 5 — The side channels (only when asked)

Add them one at a time, each with a one-line reason.

```
                    ┌─────────────┐
   Django ─────────►│    Redis    │
                    └──┬───┬───┬──┘
                       │   │   │
        broker ────────┘   │   └──── throttle counters
                           │
                    channel layer
                           │
          ┌────────────────┴────────────────┐
          ▼                                 ▼
   Celery worker                  WebSocket consumer
   • embed documents              • /ws/notifications/
   • send email                   • push-only signal
          │                                 │
          ▼                                 ▼
   pgvector chunks                    Browser refetches
```

Say: *"Redis does three unrelated jobs here — broker, channel layer, and the
throttle cache. All three are optional locally; each falls back to an in-process
equivalent."*

---

## Step 6 — The AI pipeline (its own diagram)

Draw this **separately**, not on the main diagram.

```
INGESTION (async)
  upload ──► post_save signal ──► EmbeddingJob ──► Celery (after commit)
                                                       │
        extract (pypdf/docx) ──► chunk (220w / 40 overlap) ──► embed (384-dim)
                                                       │
                                            bulk_create + HNSW index

RETRIEVAL + GENERATION (sync)
  question ──► sanitize ──► embed ──► cosine kNN  ◄── WORKSPACE FILTER FIRST
                                          │
                              top 6, distance ≤ 0.75
                                          │
                     + structured context (projects, task counts)
                                          │
                     fence as untrusted + guardrails
                                          │
                                    LLM provider
                                          │
                          {answer, sources, confidence}
```

Circle the workspace filter and say: *"That filter is why the AI can never leak
across tenants. `workspace_id` is denormalised onto the chunk table specifically
so it's one indexed predicate on the hot path."*

---

## Step 7 — The data model (if asked)

Do **not** draw 19 tables. Draw the spine:

```
                    USER
                     │
           WORKSPACE_MEMBER (role)
                     │
                 WORKSPACE  ◄── everything below has workspace_id
                     │
      ┌──────────────┼───────────────┬──────────────┐
   PROJECT       DOCUMENT        COMMENT        ACTIVITY
      │              │               │
    TASK      DOCUMENT_CHUNK      MENTION
      │        (vector 384)          │
   HANDOVER                    NOTIFICATION
```

Say: *"Nineteen tables, but the shape is: a user joins a workspace with a role,
and everything else hangs off the workspace. Comments and activities point at any
object through a generic foreign key."*

---

## Step 8 — Deployment (if asked)

```
   ┌────────────┐   ┌──────────┐
   │  frontend  │   │   web    │  uvicorn, 3 workers
   │ next start │   │  ASGI    │  runs migrate on start
   └────────────┘   └────┬─────┘
                         │
                  ┌──────┴──────┐
                  │             │
              ┌───▼───┐    ┌────▼────┐    ┌──────────┐
              │  db   │    │  redis  │◄───│  worker  │
              │pgvector│   │         │    │  celery  │
              └───────┘    └─────────┘    └──────────┘
```

Say: *"Five services in docker compose. Web and worker share one image so they
can't drift — only the command differs. And I'd flag what's missing: no reverse
proxy, and uploaded files aren't serveable in production because `/media/` is only
served when DEBUG is on."*

Volunteering that gap while drawing is a strong move.

---

## The four sentences to say while drawing

Place each one at the moment you draw the thing it describes.

1. **At the tenancy box:** *"Every object hangs off a workspace, and one base
   class enforces it on every query."*
2. **At the permission layer:** *"Cross-tenant reads return 404, not 403 — the row
   was never in the queryset, so the API never confirms an id exists."*
3. **At Redis:** *"All three of these degrade. Postgres is the only hard
   dependency; local development needs nothing else."*
4. **At the AI box:** *"The model has no tools. It can read workspace-scoped
   context and produce text — it never writes."*

---

## Handling common interruptions

| They ask | Do this |
|---|---|
| "Where's authentication?" | Add the three markers from Step 4. Say only the third is security |
| "How does this scale?" | Circle PostgreSQL. Say connection pooling is the first ceiling, then local file storage |
| "What if Redis dies?" | Point at each of the three arrows and give its fallback |
| "Where would you cache?" | Circle `/dashboard/` and `/analytics/`. Say 30s and 10min |
| "Show me a request end to end" | Trace creating a task with your finger, naming each layer |
| "What's the hardest part?" | The handover approval — two tables, two notifications, three cache invalidations |
| "What would you change?" | Circle the token box. httpOnly refresh cookie |

---

## What not to draw

- **All 19 tables.** Draw eight and say "plus AI and audit tables".
- **Every module.** Draw the four that matter: workspaces, handovers, knowledge,
  AI.
- **A layered box diagram with no arrows.** Data flow is the point; direction is
  the information.
- **Microservices you don't have.** It's a monolith. Say so — and say when you'd
  split it (the knowledge/AI seam, when embedding load competes with web
  traffic).

---

## The 60-second version, if that's all you get

```
Browser → Next.js → fetch+JWT → Django/DRF → PostgreSQL+pgvector
                                    │
                          [WorkspaceScopedViewSet]
                           every query filtered by
                           workspace membership
                                    │
                              Redis → Celery (embedding, email)
                                    → WebSocket (notifications)
```

> "Multi-tenant workspace app. Django REST on Postgres, Next.js front end. The
> organising idea is that every object belongs to a workspace and one base class
> enforces that on every query. Two things go beyond CRUD: a manager-reviewed
> handover workflow that reassigns the task only on approval, and a RAG assistant
> using pgvector, scoped to the workspace. Celery handles embedding and email;
> websockets push notifications with a polling fallback."
