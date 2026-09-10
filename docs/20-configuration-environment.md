# 20 — Configuration & Environment

[← Back to index](README.md)

> **No secret values appear in this file.** Variable names and shapes only.
> Actual values are shown as `<hidden>`.

---

## 1. Where configuration lives

```
nexora/
├── .env                        ← docker compose interpolation (gitignored ✅)
├── .env.docker.example         ← committed template, placeholders only
├── docker-compose.yml          ← reads ${VAR} from the root .env
│
├── backend/
│   ├── .env                    ← Django settings (gitignored ✅)
│   ├── .env.example            ← committed template, placeholders only
│   └── config/settings/{base,development,production,test}.py
│
└── frontend/
    ├── .env                    ← NEXT_PUBLIC_API_URL (gitignored ✅)
    ├── next.config.ts          ← currently an empty config object
    └── src/config/env.ts       ← zod validation of public env vars
```

**Verified:** `git ls-files | grep env` returns only `.env.docker.example` and
`backend/.env.example`. No real `.env` file is tracked. Both committed examples
contain placeholders (`change-me…`, empty strings) — no live credentials.

---

## 2. How the backend reads configuration

```python
env = environ.Env(
    DEBUG=(bool, False),
    SECRET_KEY=(str, ""),
    ALLOWED_HOSTS=(list, []),
    CORS_ALLOWED_ORIGINS=(list, []),
)
environ.Env.read_env(BASE_DIR / ".env")     # no-op when real env vars are injected
```
`backend/config/settings/base.py:24-32`

`django-environ`. Typed accessors are used throughout: `env.int()`, `env.bool()`,
`env.float()`, `env.db()`, and `env("X", default=...)`.

`read_env` is a no-op when the file is absent, which is exactly what happens in
Docker and CI where variables are injected directly.

---

## 3. Backend environment variables — complete list

### Core

| Variable | Type | Default | Purpose |
|---|---|---|---|
| `DJANGO_SETTINGS_MODULE` | str | `config.settings.development` | Which settings module. Docker sets `config.settings.production` |
| `SECRET_KEY` | str | `""` | **Required.** Django signing key, and the JWT signing fallback. `<hidden>` |
| `DEBUG` | bool | `False` in base, `True` in development | Debug pages, browsable API, `/media/` serving |
| `ALLOWED_HOSTS` | list | `[]` (dev: localhost, 127.0.0.1, 0.0.0.0) | Host header validation. Comma-separated |
| `CORS_ALLOWED_ORIGINS` | list | `[]` (dev: `http://localhost:3000`, `http://127.0.0.1:3000`) | Browser origins allowed to call the API **and** to open a websocket |

### Database

| Variable | Type | Purpose |
|---|---|---|
| `DATABASE_URL` | url | **Required.** `postgres://<user>:<hidden>@<host>:5432/<db>`. Parsed by `env.db()`. The database must have the `vector` extension available |

### Redis and derived services

| Variable | Default | Purpose |
|---|---|---|
| `REDIS_URL` | `redis://localhost:6379/0` | Base URL the other three default to |
| `CACHE_URL` | `REDIS_URL` | Django cache — **throttle counters** |
| `CELERY_BROKER_URL` | `REDIS_URL` | Task queue |
| `CELERY_RESULT_BACKEND` | `REDIS_URL` | Task results |
| `CHANNEL_LAYER_URL` | `REDIS_URL` | WebSocket channel layer |

Split so you can point them at different Redis databases or instances.

### JWT

| Variable | Default | Purpose |
|---|---|---|
| `JWT_ACCESS_TOKEN_LIFETIME_MINUTES` | `15` | Access token lifetime |
| `JWT_REFRESH_TOKEN_LIFETIME_DAYS` | `7` | Refresh lifetime. **Must stay in sync with `MAX_AGE` in `frontend/src/lib/auth/token-storage.ts:14`** |
| `JWT_SIGNING_KEY` | `""` → falls back to `SECRET_KEY` | Separate JWT key. `<hidden>` |

### Rate limiting

| Variable | Default | Scope |
|---|---|---|
| `THROTTLE_ANON` | `60/min` | Anonymous, by IP |
| `THROTTLE_USER` | `1000/hour` | Authenticated, by user |
| `THROTTLE_LOGIN` | `10/min` | Login, by IP |
| `THROTTLE_REGISTER` | `5/hour` | Register, by IP |
| `THROTTLE_PASSWORD_RESET` | `5/hour` | Reset, by IP |
| `THROTTLE_AI` | `30/hour` | AI endpoints, by user |

Format is DRF's `"<number>/<period>"` where period is `sec`/`min`/`hour`/`day`.

### Email

| Variable | Default | Purpose |
|---|---|---|
| `EMAIL_BACKEND` | SMTP (base), console (development) | Swap to console to print emails instead of sending |
| `EMAIL_HOST` | `""` | SMTP server |
| `EMAIL_PORT` | `587` | |
| `EMAIL_HOST_USER` | `""` | SMTP username |
| `EMAIL_HOST_PASSWORD` | `""` | `<hidden>` |
| `EMAIL_USE_TLS` | `True` | |
| `EMAIL_TIMEOUT` | `10` | Seconds. Bounded so a hung SMTP server cannot hang a worker |
| `DEFAULT_FROM_EMAIL` | `Nexora <no-reply@nexora.app>` | |
| `FRONTEND_URL` | `http://localhost:3000` | **Every link in every outgoing email is built from this.** Trailing slash stripped |
| `PASSWORD_RESET_TIMEOUT` | `86400` (24h) | Reset link validity |

### Celery

| Variable | Default | Purpose |
|---|---|---|
| `CELERY_TASK_ALWAYS_EAGER` | `False` (base) / `True` (development) | Run tasks inline instead of queueing |
| `CELERY_TASK_SOFT_TIME_LIMIT` | `600` | Graceful kill for a long embedding job |
| `CELERY_TASK_TIME_LIMIT` | `660` | Hard kill |

### AI

| Variable | Default | Purpose |
|---|---|---|
| `AI_LLM_PROVIDER` | `gemini` | Default chat provider |
| `AI_CHAT_MODEL` | `gemini-3.6-flash` | Default model |
| `AI_TEMPERATURE` | `0.2` | Low — this is a factual assistant |
| `AI_MAX_TOKENS` | `1024` | Response cap |
| `AI_EMBEDDING_PROVIDER` | `sentence_transformer` | Only this one is implemented |
| `AI_EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | 384 dimensions |
| `AI_CHUNK_SIZE_WORDS` | `220` | Chunk window |
| `AI_CHUNK_OVERLAP_WORDS` | `40` | Chunk overlap |
| `AI_EMBED_BATCH_SIZE` | `32` | Encode batch |
| `AI_SEARCH_TOP_K` | `6` | Chunks retrieved per query |
| `AI_SEARCH_MAX_DISTANCE` | `0.75` | Cosine distance cut-off |
| `AI_MAX_INPUT_CHARS` | `4000` | Prompt-abuse cap |
| `GEMINI_API_KEY` | `""` | `<hidden>`. Per-workspace keys override it |
| `OPENAI_API_KEY` | `""` | `<hidden>` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Local LLM |
| `AI_FIELD_ENCRYPTION_KEY` | `""` → derived from `SECRET_KEY` | `<hidden>`. Fernet key for stored API keys |

`EMBEDDING_DIM = 384` is **hard-coded, not an env var** — deliberately, because it
is baked into the pgvector column at migration time (`base.py:336-338`).

### Production only

| Variable | Default | Purpose |
|---|---|---|
| `SECURE_SSL_REDIRECT` | `True` | Set `False` when TLS terminates at a proxy in front |
| `SECURE_HSTS_SECONDS` | `2592000` (30 days) | HSTS max-age |

---

## 4. Frontend environment

Exactly **one** public variable:

| Variable | Default | Purpose |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000/api/v1` | Base URL of the API |

Validated at import time with zod:

```ts
const envSchema = z.object({
  NEXT_PUBLIC_API_URL: z.string().url("NEXT_PUBLIC_API_URL must be a valid URL")
                        .default("http://localhost:8000/api/v1"),
});
const parsed = envSchema.safeParse({ NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL });
if (!parsed.success) { console.error(...); throw new Error("Invalid environment variables"); }
```
`frontend/src/config/env.ts`

Two things this file's comment explains:

1. Next.js only inlines `NEXT_PUBLIC_`-prefixed variables into the client bundle,
   and they must be referenced **statically** — `process.env[key]` with a dynamic
   key does not work.
2. Validating once here means a misconfigured deploy fails fast with a clear
   message instead of producing confusing runtime errors deep in the app.

### The build-time trap

`NEXT_PUBLIC_*` values are **baked into the JavaScript bundle at build time**, not
read at runtime. The Dockerfile therefore takes it as a build arg:

```dockerfile
ARG NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN pnpm build
```
`frontend/Dockerfile:26-30`

and compose passes it under `build.args`, not `environment`
(`docker-compose.yml:132-135`), with the comment: *"Baked into the client bundle
at build time, so it must be the URL a browser can reach — not the internal
service name."*

**This is the single most common deployment mistake with this stack.** Setting
`NEXT_PUBLIC_API_URL=http://web:8000/api/v1` looks right but produces a bundle
whose fetches resolve `web` in the *user's browser*, where it does not exist.

The WebSocket URL is derived from the same variable — `lib/realtime.ts` swaps the
protocol to `ws`/`wss` and replaces the path with `/ws/notifications/`. So one
variable configures both transports.

---

## 5. Docker compose variables

Read from the **root** `.env` by `${VAR}` interpolation.

| Variable | Default in compose | Used by |
|---|---|---|
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | `nexora` / `nexora` / `nexora` | `db`, and composed into `DATABASE_URL` |
| `POSTGRES_PORT` | `5432` | host port map |
| `REDIS_PORT` | `6379` | host port map |
| `BACKEND_PORT` | `8000` | host port map |
| `FRONTEND_PORT` | `3000` | host port map |
| `DJANGO_SETTINGS_MODULE` | `config.settings.production` | `web`, `worker` |
| `SECRET_KEY` | **required** (`${SECRET_KEY:?...}`) | `web`, `worker` |
| `DEBUG`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `FRONTEND_URL`, `SECURE_SSL_REDIRECT` | see compose | `web`, `worker` |
| `EMAIL_*`, `DEFAULT_FROM_EMAIL` | console backend by default | `web`, `worker` |
| `AI_LLM_PROVIDER`, `GEMINI_API_KEY`, `OPENAI_API_KEY`, `AI_FIELD_ENCRYPTION_KEY` | empty | `web`, `worker` |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000/api/v1` | `frontend` **build arg** |

The backend environment block is a YAML anchor `&backend_env` reused by the
worker with `*backend_env`, so the two services **cannot drift**
(`docker-compose.yml:62, 110`).

### The `$` gotcha

The root README warns: `SECRET_KEY` must not contain `$`, because compose reads
it as a variable reference and strips it. Generate one with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

`token_urlsafe` produces only `[A-Za-z0-9_-]`, so it is safe by construction.

---

## 6. Settings module selection

| Context | Module | How |
|---|---|---|
| `manage.py runserver` | `config.settings.development` | Default in `manage.py` / `asgi.py` |
| `manage.py test` | `config.settings.test` | Selected automatically |
| Docker | `config.settings.production` | `DJANGO_SETTINGS_MODULE` env var |
| CI (checks) | `config.settings.development` | Explicit env in `ci.yml:48` |
| CI (tests) | `config.settings.test` | Automatic |
| Celery worker | inherits `DJANGO_SETTINGS_MODULE` | `config/celery.py:18` |

---

## 7. Non-environment configuration

Values that are code, not config:

| Constant | Where | Note |
|---|---|---|
| `EMBEDDING_DIM = 384` | `base.py:352` | Baked into the DB column |
| `PAGE_SIZE = 20` | `base.py:197` and `frontend/src/lib/constants.ts:180` | **Duplicated** — must be kept in sync manually |
| `EXPORT_LIMIT = 10_000` | `apps/activities/views.py:16` | CSV row cap |
| `_HISTORY_TURNS = 10` | `apps/ai/views.py:48` | Chat context window |
| `RETRY_DELAYS` | `use-notification-socket.ts:10` | Socket backoff |
| `MAX_AGE = 7 days` | `token-storage.ts:14` | **Must match `JWT_REFRESH_TOKEN_LIFETIME_DAYS`** |
| `API_ROUTES`, `ROUTES` | `frontend/src/lib/constants.ts` | Every path in the app |

The two duplicated values — `PAGE_SIZE` and the refresh lifetime — are the ones
to watch. Changing one side silently desynchronises the app.

---

## 8. Configuration checklist for a new environment

**Backend, minimum:**
```
DJANGO_SETTINGS_MODULE=config.settings.production
SECRET_KEY=<hidden>
DATABASE_URL=postgres://<user>:<hidden>@<host>:5432/<db>
ALLOWED_HOSTS=api.example.com
CORS_ALLOWED_ORIGINS=https://app.example.com
FRONTEND_URL=https://app.example.com
REDIS_URL=redis://<host>:6379/0
```

**Backend, for email:** `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`,
`DEFAULT_FROM_EMAIL`.

**Backend, for AI:** `GEMINI_API_KEY` (or per-workspace keys) and
`AI_FIELD_ENCRYPTION_KEY`.

**Frontend, at build time:** `NEXT_PUBLIC_API_URL=https://api.example.com/api/v1`.

**Database:** the `vector` extension must be installable. The migration runs
`CREATE EXTENSION IF NOT EXISTS vector`, which needs superuser rights on most
managed PostgreSQL services unless the extension is pre-approved.

---

**Next:** [21 — Local Development](21-local-development.md)
