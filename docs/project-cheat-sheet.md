# Nexora — Cheat Sheet

[← Docs index](README.md) · Read this in two minutes before an interview.

---

## What it is

**Multi-tenant team workspace.** Projects, tasks, documents, formal
manager-reviewed **task handovers**, threaded comments with @mentions, realtime
notifications, an append-only audit log, workspace analytics, and an **AI
assistant** doing RAG over the workspace's own documents.

> **One sentence:** Every object belongs to a workspace, and one base class
> enforces that on every query — so tenant isolation is structural.

---

## Stack

| | |
|---|---|
| Frontend | Next.js 16 (App Router) · React 19 · TypeScript · Tailwind 4 · shadcn/ui · **TanStack Query** · react-hook-form + zod |
| Transport | **native `fetch` wrapper** — no Axios |
| Backend | Django 5.1 · DRF · SimpleJWT · django-filter · drf-spectacular |
| Database | **PostgreSQL 16 + pgvector** |
| Realtime | Django Channels + Redis · polling fallback |
| Jobs | Celery + Redis · falls back to inline |
| AI | sentence-transformers (384-dim) · Gemini / OpenAI / Ollama |
| Deploy | Docker compose (5 services) · GitHub Actions CI |

---

## Frontend map

```
src/
├── proxy.ts            edge route guard (cookie presence only)
├── config/env.ts       zod-validated NEXT_PUBLIC_API_URL
├── app/
│   ├── layout.tsx      html + <Providers>
│   ├── providers.tsx   QueryClient → Theme → Auth → Toaster
│   ├── (auth)/         login · register · forgot/reset password
│   └── (app)/
│       ├── layout.tsx  ⭐ THE auth gate + sidebar + WorkspaceProvider
│       └── 32 pages    dashboard · analytics · projects · tasks · handovers
│                       documents · ai/* · activity · search · settings
├── components/  ui(29) shared(13) layout(9) ai(14) comments(6) auth(5) …
├── hooks/       16 × use-*.ts   (TanStack Query)
├── lib/
│   ├── api/client.ts   ⭐ JWT · single-flight refresh · errors
│   ├── api/*.ts        14 typed endpoint files
│   ├── constants.ts    ⭐ API_ROUTES · ROUTES · STORAGE_KEYS
│   └── auth/token-storage.ts   cookies
├── providers/   auth-provider · workspace-provider
└── types/       14 hand-mirrored serializer shapes
```

**Data path:** `page.tsx → hooks/use-*.ts → lib/api/*.ts → lib/api/client.ts`

---

## Backend map

```
backend/
├── config/
│   ├── settings/{base,development,production,test}.py
│   ├── urls.py     /api/v1/* → 13 app URLConfs
│   ├── asgi.py     HTTP | WebSocket protocol split
│   └── celery.py
└── apps/
    ├── common/     ⭐ base models · permissions · WorkspaceScopedViewSet
    │               throttling · email · channels_auth
    ├── accounts/   custom email-based User + 6 auth views
    ├── workspaces/ tenancy + roles + transfer-ownership
    ├── projects/ tasks/ documents/ handovers/      the content apps
    ├── comments/ mentions/ notifications/ activities/ invitations/
    ├── knowledge/  extract → chunk → embed → pgvector search
    ├── ai/         RAG · providers · prompts · security · summaries
    └── core/       health · dashboard · analytics · seed_demo
```

**Request path:** `urls.py → ViewSet → permission → serializer → model → SQL`
**+ signals** → audit row, notification, embedding job

---

## API — `/api/v1/`

| Area | Endpoints |
|---|---|
| Auth | `register` `login` `refresh` `logout` `me` `password-reset` `password-reset/confirm` |
| Workspaces | CRUD · `members` · `members/{id}` · `transfer-ownership` |
| Invitations | CRUD by **token** · `accept` `reject` `resend` |
| Projects | CRUD · `archive` · `restore` |
| Tasks | CRUD |
| **Handovers** | CRUD · **`review`** · `export` (PDF) |
| Documents | CRUD (multipart) · `reindex` |
| Comments | CRUD · `reply` |
| Notifications | list · `read` · `read-all` · `unread-count` |
| Activities | list · `export` (CSV) |
| AI | `chat` `search` `summarize` `generate-tasks` `settings` `conversations` `prompt-templates` |
| Core | `health` (public) · `dashboard` · `analytics` |
| Realtime | `WS /ws/notifications/?token=` |

Every list: `{count, next, previous, results}`, page size **20**, plus
`?search=` `?ordering=` `?page=`.

---

## Authentication

```
login → {access(15m), refresh(7d), user}
      → cookies (NOT httpOnly — so proxy.ts can read them)
      → Authorization: Bearer on every request
      → 401 → single-flight refresh → retry once
      → refresh rotates + blacklists the old token
      → logout blacklists + clears + queryClient.clear()
```

**Three guards:** `proxy.ts` (cookie presence) → `(app)/layout.tsx`
(`useAuth`) → **DRF permissions (the only real boundary)**.

**Roles:** owner > admin > manager > member.
`REVIEWER_ROLES = (owner, admin, manager)` — review handovers.
**Manager's only distinguishing power.**

---

## Database — 19 tables

```
accounts_user
  └─ workspaces_workspacemember (role) ─► workspaces_workspace  ⭐ TENANT
                                              │  everything below has workspace_id
      ├─ projects_project ─► tasks_task ─► handovers_handover
      ├─ documents_document ─► knowledge_documentchunk (vector 384, HNSW)
      │                    └─► knowledge_embeddingjob
      ├─ comments_comment ─► mentions_mention
      ├─ notifications_notification
      ├─ activities_activity        (append-only, signal-written)
      ├─ invitations_invitation
      └─ ai_aiconversation ─► ai_aimessage
         ai_aisettings · ai_searchhistory · ai_prompttemplate
```

**Every table:** UUID pk · `created_at` · `updated_at` · usually
`created_by`/`updated_by` · usually `workspace_id`.

---

## The eight modules

| Module | Backend | Frontend |
|---|---|---|
| Workspaces & membership | `workspaces` `invitations` | `/workspaces` `/invitations` |
| Projects & tasks | `projects` `tasks` | `/projects*` `/tasks*` |
| **Handovers** | `handovers` | `/handovers*` |
| Documents & knowledge | `documents` `knowledge` | `/documents*` |
| **AI assistant** | `ai` | `/ai/*` |
| Collaboration | `comments` `mentions` `notifications` | inline + `/notifications` |
| Activity & audit | `activities` | `/activity` |
| Dashboard & analytics | `core` | `/dashboard` `/analytics` |

---

## Key business logic

**Handover** — can't hand to yourself · recipient must be a member · only the
submitter edits · pending only · task can never be swapped · only
owner/admin/manager reviews · **once** · **rejection requires a comment** ·
approval sets `task.assignee` · both outcomes notify · PDF export.

**Tenancy** — `workspace` derived from parent, never client-supplied · assignee
must be a member · cross-tenant read = **404**.

**Mentions** — `@[Name](uuid)` · members only · not yourself · **idempotent
sync**, so editing doesn't re-notify.

**Notifications** — never self-notify · pushed **after commit** · push failure
swallowed · the socket carries a **signal, not data**.

**AI** — retrieval workspace-filtered · content fenced as untrusted · guardrails
· **generated tasks never persisted**, they go through the normal Task API.

**Audit** — signal-written · append-only · `metadata` is a snapshot ·
suppressed during workspace delete to avoid FK violations.

---

## Signals — the invisible wiring

| App | Trigger | Effect |
|---|---|---|
| `activities` | save/delete × 7 models | audit row |
| `mentions` | Comment save | re-sync mentions, emit `user_mentioned` |
| `notifications` | `user_mentioned` + replies | `create_notification()` |
| `knowledge` | Document **create** only | queue embedding |

**No domain app imports `activities`.**
**Blind spot:** `queryset.update()`, `bulk_create`, raw SQL fire nothing.

---

## Numbers to know

| | |
|---|---|
| Access / refresh token | 15 min / 7 days |
| Page size | 20 |
| Embedding | 384 dims, `all-MiniLM-L6-v2` |
| Chunk / overlap | 220 / 40 words |
| Retrieval | top 6, distance ≤ 0.75 |
| Chat history | 10 turns |
| Throttles | login 10/min · register 5/h · reset 5/h · AI 30/h |
| Tables / pages / apps | 19 / 37 / 15 |
| Tests | 93 backend methods · 6 frontend files |

---

## Everything degrades

| Down | Behaviour |
|---|---|
| Redis broker | tasks run inline |
| Redis channels | polling every 30s |
| Redis cache | per-process throttle counters |
| SMTP | logged, 3 Celery retries |
| LLM | 502 with the provider's message |
| pgvector | clean 503 with setup instructions |
| **PostgreSQL** | the only hard dependency |

**Local dev needs nothing but PostgreSQL.**

---

## Known weaknesses — own them first

1. **Tokens not httpOnly** — deliberate, for the edge guard. Fix: backend-set
   httpOnly refresh cookie + access token in memory.
2. **Media unserveable in production** — `/media/` only served when `DEBUG=True`.
3. **Document list N+1** — 41 queries for 20 rows. Fix: `annotate` + `Prefetch`.
4. **No `CONN_MAX_AGE`** — a new DB connection per request.
5. **No `completed_at`** — analytics infers the week from `updated_at`.
6. **Empty test files** — tasks, projects, comments, mentions, documents, common.
7. **Two pending handovers per task** possible — no constraint.
8. **No error boundary** — failed fetches show infinite spinners.

---

## Running it

```bash
docker compose up --build              # everything, :3000 + :8000

# or natively (Postgres only):
cd backend  && python manage.py migrate && python manage.py runserver
cd frontend && pnpm install && pnpm dev
cd backend  && python manage.py seed_demo --owner-email you@example.com
```

Verify: `GET /api/v1/health/` → `{"status":"ok","database":"ok"}`

---

## The three lines to lead with

> Tenant isolation is **structural** — one base class on every query, and
> cross-tenant reads return 404 rather than 403.

> Everything **degrades** instead of failing. Postgres is the only hard
> dependency.

> The AI **writes nothing** — retrieval is workspace-scoped, content is fenced as
> untrusted, and generated tasks go through the normal Task API for review.
