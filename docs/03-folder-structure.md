# 03 — Folder Structure

[← Back to index](README.md)

Only folders and files that matter architecturally are documented. Build output
(`.next/`, `staticfiles/`), `node_modules/`, `venv/` and migration files are
skipped except where they carry meaning.

---

## 1. Repository root

```
nexora/
├── .env                      # local secrets for docker compose (gitignored)
├── .env.docker.example       # committed placeholder template
├── .github/workflows/ci.yml  # GitHub Actions pipeline
├── .gitignore
├── README.md                 # public-facing project README
├── docker-compose.yml        # db, redis, web, worker, frontend
├── backend/                  # Django + DRF
├── frontend/                 # Next.js
└── docs/                     # this documentation
```

| Item | What / why | Who depends on it |
|---|---|---|
| `docker-compose.yml` | The only file that describes the full runtime topology: 5 services, 4 named volumes, healthchecks and start ordering. | Anyone running the stack; CI does not use it |
| `.env` (root) | Values consumed by `docker-compose.yml` via `${VAR}` interpolation. **Gitignored and untracked** — verified. | `docker-compose.yml` only |
| `.github/workflows/ci.yml` | Three jobs: `backend`, `frontend`, `docker`. Also enforces "no model change without a migration". | GitHub |

---

## 2. `backend/`

```
backend/
├── manage.py
├── requirements.txt
├── Dockerfile
├── .env                     # backend-local settings (gitignored)
├── .env.example             # committed template
├── templates/email/         # invitation.txt/.html, password_reset, password_changed
├── config/                  # project wiring — not a feature
│   ├── settings/{base,development,production,test}.py
│   ├── urls.py
│   ├── asgi.py
│   ├── wsgi.py
│   └── celery.py
└── apps/                    # one package per domain
    ├── common/    core/     accounts/   workspaces/
    ├── projects/  tasks/    documents/  handovers/
    ├── comments/  mentions/ notifications/ activities/ invitations/
    └── knowledge/ ai/
```

### `backend/config/`

**What:** Project-level wiring. Contains no business logic.
**Why:** Django convention — settings, root URLs, and the ASGI/WSGI entry points.

| File | Role | Break it and… |
|---|---|---|
| `settings/base.py` | 372 lines: installed apps, middleware, `DATABASES` from `DATABASE_URL`, DRF defaults, throttle rates, cache, email, Celery, Channels, SimpleJWT, spectacular, CORS, and the whole `AI` config dict | Nothing starts |
| `settings/development.py` | `DEBUG=True`, permissive CORS, browsable API, **console email**, **eager Celery**, in-memory channel layer, locmem cache — the "Postgres only" local mode | Local dev needs Redis + SMTP |
| `settings/production.py` | `DEBUG=False`, JSON-only renderer, SSL redirect, HSTS, secure cookies, `SECURE_PROXY_SSL_HEADER` | Production loses hardening |
| `settings/test.py` | No Redis/broker/SMTP, **throttling off**, MD5 password hasher for speed, pinned `CORS_ALLOWED_ORIGINS` | Test suite fails or is throttled |
| `urls.py` | Mounts 13 app URLConfs under `/api/v1/`, plus admin and OpenAPI docs | No endpoint resolves |
| `asgi.py` | Splits HTTP and WebSocket protocols; wraps the socket route in origin validation and JWT auth | WebSockets stop (REST unaffected) |
| `celery.py` | Creates the Celery app and autodiscovers `tasks.py` in every app. Imported from `config/__init__.py` so `@shared_task` binds correctly however the process started | Background jobs never bind |

> Note in `settings/test.py:18-20`: `CORS_ALLOWED_ORIGINS` is pinned there rather
> than read from the environment, because `config/asgi.py` hands the list to the
> websocket `OriginValidator` at import time — `override_settings` could not
> change it afterwards.

---

### `backend/apps/common/` ⭐

**What:** The shared foundation every other app builds on.
**Why:** So the tenancy and audit rules are written once.
**Who uses it:** Every domain app.
**Change it and:** every model, viewset and permission in the project changes.

| File | Contains |
|---|---|
| `models.py` | `TimeStampedModel`, `UUIDModel`, `BaseModel`, `AuditModel`, `WorkspaceScopedModel` — all abstract, no tables of their own |
| `permissions.py` | `IsWorkspaceMember`, `IsWorkspaceAdmin`, `IsWorkspaceManager`, `IsWorkspaceOwner`, `IsWorkspaceAdminOrReadOnly` |
| `viewsets.py` | `WorkspaceScopedViewSet` — auto-filters querysets to the caller's workspaces and stamps `created_by`/`updated_by` |
| `throttling.py` | `LoginRateThrottle`, `RegisterRateThrottle`, `PasswordResetRateThrottle`, `AIRateThrottle` |
| `email.py` | `send_templated_email()`, `queue_templated_email()`, `frontend_url()` |
| `tasks.py` | `send_email_task` — Celery task with 3 retries and backoff |
| `channels_auth.py` | `JWTAuthMiddleware` for WebSocket connections |
| `tests.py` | Tenant isolation, the role matrix, and the scheduled maintenance tasks (21 tests) |

`migrations/` here contains only `__init__.py` — the abstract models create no
tables.

---

### `backend/apps/accounts/`

Custom user model keyed on email. `User.username = None`,
`USERNAME_FIELD = "email"`, UUID primary key, explicit
`db_table = "accounts_user"`.

Holds the six auth views (register, login, logout, me, password-reset,
password-reset-confirm) plus `TokenRefreshView` re-exported from SimpleJWT.
`serializers.py` also exports `build_reset_credentials()`, used by the view to
build a reset link.

**Depended on by:** every app, indirectly through `settings.AUTH_USER_MODEL`, and
directly through `UserSerializer` which is nested in almost every other
serializer.

---

### `backend/apps/workspaces/`

The tenant boundary. `Workspace` (with auto-slug) and `WorkspaceMember` (unique
per `(workspace, user)`), plus `WorkspaceRole` and the `REVIEWER_ROLES` tuple
that `handovers` and the frontend both read.

`views.py` is the most permission-dense file in the backend: a per-action
permission matrix (`get_permissions`, line 50), a nested `members` action, a
regex-routed `manage_member` action, and an atomic `transfer_ownership`.

---

### `backend/apps/{projects,tasks,documents,handovers}/`

The four "content" apps. All follow an identical five-file shape:

```
models.py       the table
serializers.py  validation + shaping
filters.py      django-filter FilterSet (query params)
views.py        a WorkspaceScopedViewSet subclass
urls.py         DefaultRouter registration
```

`handovers/` adds `pdf.py` (reportlab export). `documents/` has no extra file but
its `views.py` adds `parser_classes` for multipart upload and a `reindex` action.

Each also has a populated `tests.py` now — `projects` (12), `tasks` (15),
`documents` (17), the last covering upload validation and the authenticated
download endpoint.

---

### `backend/apps/{comments,mentions,notifications,activities,invitations}/`

The collaboration and platform apps.

| App | Distinctive file | Why it exists |
|---|---|---|
| `comments` | `permissions.py` — `IsAuthorOrWorkspaceAdmin` | Author may edit; author *or* workspace admin may delete |
| `mentions` | `services.py` + `signals.py` | Parses `@[Name](uuid)` tokens; emits a custom `user_mentioned` signal |
| `notifications` | `consumers.py`, `routing.py`, `services.py`, `handlers.py` | WebSocket push + `create_notification()` used by other apps |
| `activities` | `handlers.py`, `services.py` | Signal-driven audit trail with a delete-suppression guard |
| `invitations` | `views.py` (5 custom actions) | Token-keyed accept/reject/resend lifecycle |

---

### `backend/apps/knowledge/` and `backend/apps/ai/`

Split deliberately: **knowledge = retrieval**, **ai = generation**.

```
knowledge/
├── models.py                 DocumentChunk (vector), EmbeddingJob
├── handlers.py               post_save(Document) -> enqueue
├── tasks.py                  Celery: process_document_task
├── services/
│   ├── extractor.py          PDF / DOCX / TXT / MD -> text
│   ├── chunker.py            word-window split with overlap
│   ├── processor.py          orchestrates extract->chunk->embed->store
│   └── search.py             semantic_search() — pgvector cosine kNN
├── embeddings/
│   ├── base.py  factory.py  sentence_transformer.py
└── management/commands/reindex_documents.py

ai/
├── models.py                 AIConversation, AIMessage, AISettings,
│                             SearchHistory, PromptTemplate
├── permissions.py            resolve_workspace()
├── providers/                base, factory, gemini, openai, ollama
├── services/
│   ├── rag.py                the RAG orchestration
│   ├── prompts.py            every system/user prompt
│   ├── security.py           prompt-injection guardrails
│   ├── summarizer.py         project/task/document/activity summaries
│   ├── action_items.py       text -> suggested tasks (JSON)
│   └── crypto.py             Fernet encryption for stored API keys
└── views.py                  3 ViewSets + 5 APIViews
```

`ai` imports `knowledge.services.search`; `knowledge` never imports `ai`. That is
the layering: generation depends on retrieval, not the other way round.

---

### `backend/apps/core/`

Not a domain — "everything that isn't one". Three views (`health`, `dashboard`,
`analytics`), the `seed_demo` management command, `demo_data.py`, and the two
broadest test files in the project (`tests_smoke.py`, `tests_seed_demo.py`).

`core/views.py` imports models and serializers from **six** other apps. That
makes it the most coupled file in the backend, and it is a deliberate trade —
see [19-performance-scalability.md](19-performance-scalability.md).

---

### `backend/templates/email/`

Plain-text (`.txt`) email bodies with optional `.html` siblings. Rendered through
a **second, dedicated Django template engine** named `"text"` with
`autoescape: False` (`config/settings/base.py:128-134`). The comment there
explains why: with autoescaping on, an `&` in a reset URL renders as `&amp;`, so
the link arrives carrying a parameter literally named `amp;token` and the reset
silently fails.

---

## 3. `frontend/`

```
frontend/
├── package.json  pnpm-lock.yaml  pnpm-workspace.yaml
├── next.config.ts            # currently empty config object
├── tsconfig.json  eslint.config.mjs  postcss.config.mjs
├── components.json           # shadcn/ui generator config
├── vitest.config.mts  vitest.setup.ts
├── Dockerfile                # 3-stage: deps -> builder -> runner
├── .env                      # NEXT_PUBLIC_API_URL (gitignored)
├── AGENTS.md  CLAUDE.md      # agent instructions (CLAUDE.md is just "@AGENTS.md")
└── src/
    ├── proxy.ts              ⭐ edge route guard
    ├── config/env.ts         zod-validated public env
    ├── app/                  routes
    ├── components/           UI
    ├── hooks/                TanStack Query wrappers
    ├── lib/                  api client, constants, validations, utils
    ├── providers/            React Context
    └── types/                TS mirrors of DRF serializers
```

### `src/app/`

```
app/
├── layout.tsx        root; html/body + <Providers>
├── providers.tsx     QueryClient + Theme + Auth + Toaster
├── page.tsx          public landing page
├── not-found.tsx
├── globals.css
├── (auth)/           route group — bare centred card layout
│   └── login/ register/ forgot-password/ reset-password/
└── (app)/            route group — sidebar shell, auth-gated
    ├── layout.tsx    ⭐ the real client-side auth gate
    ├── dashboard/ analytics/ activity/ search/ settings/ notifications/ invitations/
    ├── projects/{,new,[id],[id]/edit}
    ├── tasks/{,new,[id],[id]/edit}
    ├── handovers/{,new,reviews,[id]}
    ├── documents/{,new,[id]}
    ├── workspaces/{,new,[id]/settings}
    └── ai/{,chat,chat/[id],conversations,search,templates,settings}
```

Parentheses make a **route group**: they organise files and give each group its
own `layout.tsx` without appearing in the URL. `/login` is served by
`app/(auth)/login/page.tsx`.

**Total: 37 `page.tsx` files.**

### `src/components/`

| Folder | Count | What lives there | Used by |
|---|---|---|---|
| `ui/` | 29 | shadcn/ui primitives — button, card, dialog, form, input, popover, sidebar, table, tabs, sonner… | everything |
| `shared/` | 13 | Cross-domain building blocks: `page-header`, `stat-card`, `status-badge`, `priority-badge`, `empty-state`, `no-workspace`, `confirm-dialog`, `data-pagination`, `search-input`, `table-skeleton`, `file-upload`, `date-picker` | most pages |
| `layout/` | 9 | `app-sidebar`, `workspace-switcher`, `nav-user`, `app-breadcrumbs`, `page-container`, `site-header`, `home-cta` | `(app)/layout.tsx`, landing |
| `ai/` | 14 | `chat-window`, `message-bubble`, `sources-panel`, `confidence-badge`, `embedding-status-badge`, `prompt-template-selector`, `ai-settings-form`… | `/ai/*` |
| `comments/` | 6 | `comment-section`, `comment-item`, `comment-form`, `mention-textarea`, `collaboration-tabs`, `comment-content` | task/project/document detail pages |
| `auth/` | 5 | `login-form`, `register-form`, `forgot-password-form`, `reset-password-form` (+1 test) | `(auth)` pages |
| `notifications/` | 3 | `notification-bell`, `notification-list`, item | `(app)/layout.tsx` header |
| `members/` | 4 | member table / role controls | workspace settings |
| `charts/` | 1 | `charts.tsx` — dependency-free SVG charts | `/analytics` |
| `handovers/`, `projects/`, `tasks/`, `documents/`, `workspaces/`, `activities/` | 2–3 each | domain forms and cards | their pages |

### `src/lib/`

| File | Role | Depended on by |
|---|---|---|
| `api/client.ts` ⭐ | The `fetch` wrapper: JWT, single-flight refresh, error normalisation | every `lib/api/*.ts` |
| `api/*.ts` (14 domain files) | Typed endpoint functions | `hooks/` |
| `api/errors.ts` | `isApiError`, `getErrorMessage`, `applyFieldErrors` | every form |
| `api/download.ts` | Authenticated blob download for PDF/CSV | handover detail, audit log |
| `constants.ts` ⭐ | `API_ROUTES`, `ROUTES`, `STORAGE_KEYS`, enum label tables, `PAGE_SIZE` | client, proxy, hooks, pages, sidebar |
| `auth/token-storage.ts` | In-memory access token + the non-secret session marker. **Never touches the refresh token**, which is httpOnly | client, auth-provider, socket, download |
| `query-client.ts` | `makeQueryClient()` with SaaS-tuned defaults | `app/providers.tsx` |
| `validations/*.ts` (8) | Zod schemas mirroring backend rules | forms |
| `realtime.ts` | Derives the `ws://`/`wss://` URL from `NEXT_PUBLIC_API_URL` | `use-notification-socket` |
| `format.ts`, `initials.ts`, `utils.ts`, `activity.ts` | Small pure helpers | components |

### `src/providers/`

| File | Owns | Consumed via |
|---|---|---|
| `auth-provider.tsx` | `user`, `isLoading`, `isAuthenticated`, `login()`, `logout()`, `setUser()` | `useAuth()` |
| `workspace-provider.tsx` | `workspaces`, `activeWorkspace`, `activeWorkspaceId`, `setActiveWorkspaceId()` | `useWorkspaceContext()` |

`AuthProvider` is mounted app-wide in `app/providers.tsx`.
`WorkspaceProvider` is mounted **only inside** `app/(app)/layout.tsx`, so the
auth pages never try to load workspaces.

### `src/types/`

14 files that hand-mirror the DRF serializers. There is no code generation from
the OpenAPI schema, so these can drift — but `pnpm typecheck` in CI catches the
frontend half of any mismatch. `types/index.ts` holds the shared `Paginated<T>`
and `ApiError` shapes.

---

## 4. "What would break if I changed…" quick table

| If you change… | These break |
|---|---|
| `apps/common/models.py` | Every model; requires a migration across all apps |
| `apps/common/viewsets.py` `get_queryset()` | **Tenant isolation for every scoped resource** |
| `apps/common/permissions.py` | Role enforcement everywhere |
| `settings.AI["EMBEDDING_DIM"]` | The pgvector column; needs a migration altering `DocumentChunk.embedding` (called out in `base.py:336-338`) |
| `lib/constants.ts` `API_ROUTES` | Every API call; also `proxy.ts` via `STORAGE_KEYS` |
| `lib/api/client.ts` | All data fetching and the auth refresh cycle |
| `providers/auth-provider.tsx` | `(app)/layout.tsx` gate, nav-user, every `useAuth()` caller |
| `providers/workspace-provider.tsx` | Every list page (all queries are workspace-gated) |
| `workspaces/models.py` `WorkspaceRole` | Permissions, handover review, sidebar, invitations, `types/workspace.ts` |
| A DRF serializer's field names | The matching file in `frontend/src/types/` — silently, until typecheck runs |

---

**Next:** [04 — Frontend Architecture](04-frontend-architecture.md)
