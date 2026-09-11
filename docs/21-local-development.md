# 21 — Local Development

[← Back to index](README.md)

Two ways to run this: Docker (everything) or native (Postgres only). Both are
documented in the root `README.md`; this file adds what the code actually
requires and why.

---

## 1. Requirements

| Tool | Version | Needed for |
|---|---|---|
| Python | 3.13+ | Backend. `Dockerfile` uses `python:3.13-slim`; CI uses 3.13 |
| Node | 20+ (Docker uses 22, CI uses 22) | Frontend |
| pnpm | 11 (CI pins it) | **Required** — the lockfile is pnpm's; npm/yarn will not match it |
| PostgreSQL | 16+ **with pgvector** | Database |
| Redis | 7 | **Optional locally** |
| Docker | any recent | Only for the compose route |

### The pgvector requirement

`CREATE EXTENSION vector` must succeed, or
`knowledge/migrations/0001_initial.py` fails and `migrate` stops. Options:

- Docker: use `pgvector/pgvector:pg16` (what compose and CI both use).
- Native: install the pgvector extension for your PostgreSQL, then
  `CREATE EXTENSION vector;` in the target database.

---

## 2. Route A — Docker (everything, one command)

```bash
cp .env.docker.example .env

# generate a SECRET_KEY with no '$' in it (compose would strip it)
python -c "import secrets; print(secrets.token_urlsafe(64))"
# paste it into .env as SECRET_KEY=...

docker compose up --build
```

Brings up five services. `web` runs `migrate --noinput` before starting uvicorn,
so the schema is created automatically.

| Service | URL | Notes |
|---|---|---|
| `db` | `localhost:5432` | pgvector/pg16, healthchecked with `pg_isready` |
| `redis` | `localhost:6379` | AOF persistence so a restart does not drop queued jobs |
| `web` | `http://localhost:8000/api/v1` | uvicorn, 3 workers, healthchecked on `/api/v1/health/` |
| `worker` | — | `celery -A config worker --concurrency=2` |
| `beat` | — | `celery -A config beat` — nightly maintenance. Exactly **one** per deployment |
| `frontend` | `http://localhost:3000` | `next start` |

Emails print to the `web` container log unless `EMAIL_HOST` is set.

**First build is slow.** The backend image installs the CPU-only torch wheel and
then the rest of `requirements.txt`. Subsequent builds reuse the layer as long as
`requirements.txt` is unchanged.

### Useful compose commands

```bash
docker compose logs -f web          # follow API logs (emails print here)
docker compose logs -f worker       # embedding job progress
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py seed_demo --owner-email you@example.com
docker compose exec db psql -U nexora -d nexora
docker compose down                 # stop
docker compose down -v              # stop AND delete the volumes (destroys data)
```

---

## 3. Route B — Native (Postgres only)

The development settings are written so **Redis, Celery and SMTP are all
optional**. `config/settings/development.py:26-29` states the goal explicitly.

| Service | Without it you get |
|---|---|
| Redis (cache) | `LocMemCache` — throttle counters are per-process, which is accurate with one process |
| Redis (channels) | `InMemoryChannelLayer` — websockets work, single process only |
| Redis (broker) | `CELERY_TASK_ALWAYS_EAGER=True` — embedding and email run inline |
| SMTP | Console email backend — messages print to the terminal |

### Backend

```bash
cd backend
python -m venv .venv
. .venv/Scripts/activate          # Windows;  source .venv/bin/activate on Unix
pip install -r requirements.txt

cp .env.example .env
# set at minimum:
#   SECRET_KEY=<hidden>
#   DATABASE_URL=postgres://<user>:<hidden>@localhost:5432/nexora

python manage.py migrate
python manage.py createsuperuser   # optional, for /admin/
python manage.py runserver         # http://localhost:8000
```

`runserver` here is **daphne's ASGI runserver**, because `daphne` precedes
`django.contrib.staticfiles` in `INSTALLED_APPS`. That is why websockets work in
development with no extra process.

### Frontend

```bash
cd frontend
pnpm install
cp .env.example .env.local          # NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
pnpm dev                            # http://localhost:3000
```

> Note: the repository currently has `frontend/.env` (gitignored) rather than
> `.env.local`. Next.js loads both; `.env.local` takes precedence. Either works.

`pnpm dev` runs `next dev --turbopack`.

### Optional — a real Celery worker

```bash
# backend/.env
REDIS_URL=redis://localhost:6379/0
CELERY_TASK_ALWAYS_EAGER=False
```

```bash
cd backend
celery -A config worker --loglevel=info
```

Only worth doing if you want to see the async path behave the way production
does. Uploads become non-blocking and you can watch job status transition
`pending → processing → completed`.

---

## 4. Ports

| Port | Service | Configurable via |
|---|---|---|
| 3000 | Next.js | `FRONTEND_PORT` (compose) |
| 8000 | Django API + WebSocket | `BACKEND_PORT` (compose) |
| 5432 | PostgreSQL | `POSTGRES_PORT` (compose) |
| 6379 | Redis | `REDIS_PORT` (compose) |
| 11434 | Ollama, if used | `OLLAMA_BASE_URL` |

**There is no dev proxy.** The frontend calls the API cross-origin at
`http://localhost:8000`, which is why `CORS_ALLOWED_ORIGINS` must include
`http://localhost:3000` — and it does by default in `development.py:12-15`.

---

## 5. Demo data

```bash
cd backend
python manage.py seed_demo --owner-email you@example.com
python manage.py seed_demo --reset --owner-email you@example.com   # re-seed clean
python manage.py seed_demo --owner-email you@example.com --skip-embedding
```

`backend/apps/core/management/commands/seed_demo.py` + `demo_data.py`.

Creates three workspaces (*Aurora Labs*, *Northwind Ops*, *Client Portal*) with
eleven teammates, twelve projects, ~60 tasks, real embedded documents, handovers
in every review state, threaded comments with @mentions, notifications,
invitations, an eight-week activity trail, and AI conversations, prompt templates
and search history.

Two properties that make it genuinely useful:

- **Enum coverage is exhaustive** — every task status × priority pair, every
  project/handover/invitation state — so every filter and every chart has data.
- **Timestamps are backdated across eight weeks**, so the analytics series,
  overdue counters and audit-log date filters are all meaningful.

`--reset` only removes the seeded workspaces and `@nexora.demo` accounts; real
data is untouched. `--skip-embedding` skips the slow local embedding pass — AI
semantic search then returns nothing.

Seeded accounts share the password `Demo@12345` (this is documented demo data,
not a secret).

The seeder uses `knowledge.handlers.ingestion_disabled()` — a context manager
that temporarily disconnects the embedding signal so bulk-loading hundreds of
documents does not trigger hundreds of embedding jobs.

---

## 6. Everyday commands

### Backend

```bash
python manage.py runserver                 # ASGI dev server
python manage.py migrate                   # apply migrations
python manage.py makemigrations            # after a model change
python manage.py makemigrations --check --dry-run   # what CI runs
python manage.py check --fail-level WARNING         # what CI runs
python manage.py test                      # full suite (uses config.settings.test)
python manage.py test apps.handovers -v 2  # one app, verbose
python manage.py shell                     # ORM console
python manage.py createsuperuser
python manage.py seed_demo --owner-email you@example.com
python manage.py reindex_documents         # re-embed everything
python manage.py spectacular --file schema.yml      # dump the OpenAPI schema
celery -A config worker --loglevel=info
```

### Frontend

```bash
pnpm dev          # next dev --turbopack
pnpm build        # production build
pnpm start        # serve the build
pnpm typecheck    # tsc --noEmit
pnpm lint         # eslint
pnpm test         # vitest run
pnpm test:watch
pnpm test:coverage
```

---

## 7. Verifying the system is up

Work through these in order — each one proves a different layer.

| # | Check | Command / URL | Expected |
|---|---|---|---|
| 1 | Database reachable | `GET http://localhost:8000/api/v1/health/` | `{"status":"ok","database":"ok"}` with 200 |
| 2 | API routing + schema | `http://localhost:8000/api/docs/` | Swagger UI listing every endpoint |
| 3 | Admin | `http://localhost:8000/admin/` | Login page |
| 4 | Frontend serving | `http://localhost:3000` | Landing page |
| 5 | Auth end to end | Register, then sign in | Redirect to `/dashboard` |
| 6 | Cookies set | DevTools → Application → Cookies | `nexora_refresh` marked **HttpOnly** on the API origin, and `nexora.session=1` on the frontend origin. **No access or refresh token should be readable by script** |
| 6b | Session survives reload | Hard-refresh a signed-in page | Stays signed in — the access token is re-minted from the refresh cookie |
| 7 | Tenancy works | Create a workspace | It appears in the sidebar switcher |
| 8 | CRUD works | Create a project, then a task | Dashboard counters increase |
| 9 | Signals work | `/activity` | `workspace.created`, `project.created`, `task.created` rows |
| 10 | Realtime works | DevTools → Network → WS | `/ws/notifications/` open, first frame `{"type":"connected"}` |
| 11 | Notifications work | Have a second user comment and @mention you | Bell badge increments without a refresh |
| 12 | Uploads work | Upload a `.txt` or `.pdf` at `/documents/new` | Row created; `embedding_status` reaches `completed` |
| 12b | Download is authenticated | Click Download on the document | File downloads; the URL is `/api/v1/documents/<id>/download/`, not `/media/` |
| 12c | Upload limits work | Try a `.html` file | Rejected with "Unsupported file type" |
| 13 | RAG works | `/ai/search` for a phrase from that document | The chunk comes back with a score |
| 14 | LLM works | `/ai/chat` ask a question | An answer with sources — needs an API key |
| 15 | Email works | Request a password reset | The email prints in the backend console |
| 16 | PDF works | Open a handover, Export PDF | A PDF downloads |

If step 1 fails, nothing else will. If step 10 fails but everything else works,
you are on the polling fallback — harmless.

---

## 8. Tips that save time

**Watch the right log.** In dev, password-reset and invitation emails print to
the **backend** terminal (console email backend). The reset link is in that
output.

**`/api/docs/` is a live client.** Swagger UI lets you authorise with a bearer
token and call any endpoint — faster than curl for exploring.

**React Query Devtools are already wired in.** `app/providers.tsx:47` mounts
`<ReactQueryDevtools initialIsOpen={false} />`, so the cache inspector is
available in dev with no setup. It is the fastest way to see which query key a
page is using and whether data is stale.

**Django admin is registered for every model** (`apps/*/admin.py`), so you can
inspect and edit rows directly at `/admin/`.

**To test the async path**, set `CELERY_TASK_ALWAYS_EAGER=False` and start a
worker. Without it, an upload blocks until embedding finishes — which is why the
first upload in a fresh dev environment feels like it hangs (it is downloading a
90 MB model).

**`manage.py test` picks `config.settings.test` automatically**, which turns
throttling off. If you see 429s in a test, you are not using that module.

---

## 9. Common first-run problems

| Symptom | Cause | Fix |
|---|---|---|
| `migrate` fails on `knowledge.0001_initial` | pgvector extension unavailable | Use the `pgvector/pgvector:pg16` image, or install the extension |
| `django.core.exceptions.ImproperlyConfigured: Set the SECRET_KEY` | `SECRET_KEY` empty | Set it in `backend/.env` |
| `env.db("DATABASE_URL")` raises | `DATABASE_URL` missing or malformed | It has no default — it is required |
| First upload appears to hang | Downloading the 90 MB embedding model, inline | Wait; or start a worker; or `--skip-embedding` in the seeder |
| CORS errors in the browser console | Frontend origin not in `CORS_ALLOWED_ORIGINS` | Development defaults already include `localhost:3000` |
| WebSocket 403 | Origin not in `CORS_ALLOWED_ORIGINS` — `OriginValidator` uses the same list | Add the frontend origin |
| `pnpm install` errors about the lockfile | Using npm or yarn | Use pnpm; the lockfile is pnpm's |
| Frontend builds but every API call fails in Docker | `NEXT_PUBLIC_API_URL` baked as an internal service name | It must be a URL the **browser** can reach |

Full symptom → cause → fix table: [23-troubleshooting.md](23-troubleshooting.md).

---

**Next:** [22 — Production Deployment](22-production-deployment.md)
