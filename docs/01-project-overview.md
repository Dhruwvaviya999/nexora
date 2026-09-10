# 01 — Project Overview

[← Back to index](README.md)

---

## 1. Name and identity

| Field | Value | Source |
|---|---|---|
| Product name | **Nexora** | `frontend/src/lib/constants.ts` → `APP.shortName` |
| Full title | "AI Knowledge & Workflow Assistant" | `APP.name`, and `SPECTACULAR_SETTINGS["TITLE"]` |
| Tagline | "Your team's knowledge base and workflow automation, powered by AI." | `APP.description` |
| Celery app name | `nexora` | `backend/config/celery.py:20` |
| Compose project | `nexora` | `docker-compose.yml:13` |

---

## 2. The problem it solves

Three problems, all visible in the code:

**a. Work context is lost when a task changes hands.**
Most trackers let you reassign a task with one click and no explanation. Nexora
makes handing work over a *formal, reviewed artefact*: the outgoing member writes
a work summary, a list of pending items and a list of resources, then a manager
approves or rejects it. Only on approval does the task's assignee actually
change. Implemented in `backend/apps/handovers/`.

**b. Team knowledge is scattered across documents nobody re-reads.**
Documents uploaded to a workspace are automatically parsed, split into
overlapping chunks, embedded as vectors and stored in pgvector. Members then ask
plain-language questions and get answers grounded in their own documents, with
citations. Implemented in `backend/apps/knowledge/` (ingestion + retrieval) and
`backend/apps/ai/` (generation).

**c. Nobody can reconstruct who changed what.**
Every create, update and delete on a project, task, document, handover, comment,
workspace or membership writes an append-only `activities_activity` row via
Django signals, filterable and exportable to CSV. Implemented in
`backend/apps/activities/`.

---

## 3. Who uses it

The user model is a person with an email; the *role* is per workspace, stored on
`workspaces_workspacemember.role` (`backend/apps/workspaces/models.py:68`).

| Role | Can do | Enforced by |
|---|---|---|
| **Owner** | Everything, plus transfer ownership and delete the workspace | `IsWorkspaceOwner` |
| **Admin** | Manage members and invitations, edit the workspace, moderate comments, review handovers, change AI settings | `IsWorkspaceAdmin`, `IsWorkspaceAdminOrReadOnly` |
| **Manager** | Everything a member can do, **plus review handovers** | `IsWorkspaceManager` / `REVIEWER_ROLES` |
| **Member** | Create and edit content, submit handovers, comment, use AI | `IsWorkspaceMember` |

`REVIEWER_ROLES = (OWNER, ADMIN, MANAGER)` — `backend/apps/workspaces/models.py:25`.
The frontend mirrors this list in `frontend/src/types/workspace.ts:8` to decide
whether to show the "Reviews" sidebar item and the approve/reject card.

A person can belong to many workspaces with a different role in each. The
"current" workspace is a frontend concept held in
`frontend/src/providers/workspace-provider.tsx` and persisted to `localStorage`.

---

## 4. Major modules

Eight business modules, each documented in [`modules/`](modules/):

| Module | Backend app(s) | Frontend routes |
|---|---|---|
| [Workspaces & membership](modules/workspaces.md) | `workspaces`, `invitations` | `/workspaces`, `/invitations` |
| [Projects & tasks](modules/projects-tasks.md) | `projects`, `tasks` | `/projects`, `/tasks` |
| [Handovers](modules/handovers.md) | `handovers` | `/handovers`, `/handovers/reviews` |
| [Documents & knowledge](modules/documents-knowledge.md) | `documents`, `knowledge` | `/documents` |
| [AI assistant](modules/ai-assistant.md) | `ai` | `/ai/*` |
| [Collaboration](modules/collaboration.md) | `comments`, `mentions`, `notifications` | inline + `/notifications` |
| [Activity & audit](modules/activity-audit.md) | `activities` | `/activity` |
| [Dashboard & analytics](modules/dashboard-analytics.md) | `core` | `/dashboard`, `/analytics` |

---

## 5. Technology and why each piece is there

### Frontend

| Choice | Role in this project |
|---|---|
| **Next.js 16 App Router** | File-system routing, route groups for two different layouts, and an edge middleware (`proxy.ts`) that can bounce requests before a page renders. |
| **React 19** | UI runtime. Almost every page is a Client Component (`"use client"`) because they all read auth/workspace context. |
| **TypeScript** | `src/types/*` mirror the DRF serializers by hand, so a serializer change surfaces as a compile error in CI (`pnpm typecheck`). |
| **Tailwind 4 + shadcn/ui** | 29 components under `src/components/ui/` are shadcn primitives (Radix under the hood) rather than a monolithic component library. |
| **TanStack Query** | All server data. 16 `use-*` hooks wrap the API layer; caching, refetching and invalidation live here instead of in `useEffect`. |
| **react-hook-form + zod** | Form state and client-side validation. Zod schemas in `src/lib/validations/` restate backend constraints so the user gets errors without a round trip. |
| **Native `fetch`** | No Axios. `src/lib/api/client.ts` is a ~140-line wrapper that adds the JWT, does single-flight refresh on 401, and normalises errors into `ApiError`. |

### Backend

| Choice | Role in this project |
|---|---|
| **Django 5.1** | ORM, migrations, auth primitives (password hashing, reset tokens), admin, signals. |
| **DRF** | ViewSets give CRUD + filtering + pagination per model with about 10 lines each; serializers handle validation both ways. |
| **SimpleJWT** | Stateless access tokens, rotating refresh tokens, and a blacklist table for revocation. |
| **django-filter** | Declarative query-param filtering (`FilterSet` classes per app). |
| **drf-spectacular** | Generates the OpenAPI schema served at `/api/schema/`, `/api/docs/`, `/api/redoc/`. |
| **Channels + daphne/uvicorn** | WebSocket push for notifications. `runserver` is Channels' ASGI version, so sockets work in dev with no extra process. |
| **Celery + Redis** | Embedding jobs and outgoing email. Both fall back to running inline when no broker is configured. |
| **pgvector** | Vector column and cosine-distance operator inside the same PostgreSQL instance — no separate vector database. |
| **reportlab** | Renders a handover to PDF (`backend/apps/handovers/pdf.py`). |

### Data

- **PostgreSQL 16** with the `vector` extension. The extension is created by a
  migration operation, `VectorExtension()` in
  `backend/apps/knowledge/migrations/0001_initial.py:24`.
- **Redis** serves three separate jobs: Celery broker/result backend, Channels
  layer, and the DRF throttle counter cache. All three are optional locally.

### External services

| Service | Used for | Configured by |
|---|---|---|
| SMTP | Invitations, password reset, password-changed notice | `EMAIL_*` env vars |
| Google Gemini | Default chat LLM | `GEMINI_API_KEY`, or a per-workspace key |
| OpenAI | Alternative chat LLM | `OPENAI_API_KEY`, or a per-workspace key |
| Ollama | Local LLM option | `OLLAMA_BASE_URL` |
| Hugging Face | Downloads `all-MiniLM-L6-v2` on first embed | implicit; cached in a Docker volume |

There is **no** payment provider, no analytics SDK, no cloud object store and no
ERP integration in this codebase.

---

## 6. Authentication approach in one paragraph

Email-based login (there is no username — `User.username = None`,
`USERNAME_FIELD = "email"`). Credentials are exchanged for a JWT pair: a 15-minute
access token and a 7-day refresh token. Refresh tokens rotate on use and the old
one is blacklisted. The frontend keeps both in cookies so the Next.js edge proxy
can see them, and attaches the access token as a `Bearer` header on every API
call. Authorization is separate from authentication: DRF permission classes read
the caller's `WorkspaceMember.role` for the object being touched.

---

## 7. Deployment approach

`docker-compose.yml` defines five services — `db` (pgvector/pg16), `redis`,
`web` (Django under uvicorn, 3 workers, runs `migrate` on start), `worker`
(Celery, concurrency 2), and `frontend` (Next.js production server). The backend
and worker share **one image** so they cannot drift. CI
(`.github/workflows/ci.yml`) runs the Django test suite against real Postgres +
Redis, then typechecks, lints, tests and builds the frontend; pushes to
`main`/`develop` additionally build both Docker images.

There is **no** Nginx config, systemd unit, Kubernetes manifest or cloud
deployment script in the repository. See
[22-production-deployment.md](22-production-deployment.md).

---

## 8. In plain words

> Nexora is a shared office building. Each company rents a floor — that's a
> *workspace*, and nothing on one floor is visible from another. Inside a floor
> you have projects, the tasks inside them, and a filing cabinet of documents.
> When someone leaves a task to a colleague, they don't just slide the folder
> across the desk: they fill in a handover form, and a manager signs it before
> the task really changes hands. A clerk in the corner writes down every single
> thing that happens, in pen, in a ledger nobody can erase. And there's a
> research assistant who has read every document on your floor — and only your
> floor — who you can ask questions in plain English.

---

## 9. Delivery history

The root `README.md` documents eight delivery phases (setup → auth → CRUD →
collaboration → AI + handovers → polish → analytics/PDF/audit → production
readiness). Several code comments still refer to these phase numbers, e.g.
"Phase 5 — AI Knowledge Assistant" in `backend/config/settings/base.py:78`. This
is history, not architecture; a few of those comments are now stale (see
[25-known-limitations.md](25-known-limitations.md)).

---

**Next:** [02 — System Architecture](02-system-architecture.md)
