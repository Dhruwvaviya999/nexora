# 23 — Troubleshooting

[← Back to index](README.md)

Every entry follows: **symptom → likely cause → where to look → how to diagnose →
how to fix.** All causes are derived from this codebase, not generic advice.

---

## 1. Startup

### `migrate` fails on `knowledge.0001_initial`

**Cause:** the PostgreSQL `vector` extension is not available. The migration runs
`VectorExtension()` → `CREATE EXTENSION IF NOT EXISTS vector`.
**Look at:** `backend/apps/knowledge/migrations/0001_initial.py:24`.
**Diagnose:** `psql -c "SELECT * FROM pg_available_extensions WHERE name='vector';"`
**Fix:** use the `pgvector/pgvector:pg16` image (compose and CI both do), or
install pgvector for your server. On managed PostgreSQL the extension usually
needs superuser rights or an allow-list entry.

### `ImproperlyConfigured: The SECRET_KEY setting must not be empty`

**Cause:** `SECRET_KEY` defaults to `""` and Django rejects that.
**Fix:** set it in `backend/.env`. For compose, the root `.env` — and it must not
contain `$`, which compose reads as a variable reference and strips.

### `env.db("DATABASE_URL")` raises `ImproperlyConfigured`

**Cause:** `DATABASE_URL` has **no default** (`base.py:146`) — it is required.
**Fix:** `DATABASE_URL=postgres://<user>:<hidden>@localhost:5432/nexora`

### Django will not start: "Apps aren't loaded yet"

**Cause:** something imported a model before `get_asgi_application()` ran.
`config/asgi.py:19-21` explains the required ordering.
**Fix:** keep model-touching imports below `django_asgi_application = get_asgi_application()`,
and import SDKs lazily inside functions — the pattern used in
`common/channels_auth.py:25-28`.

### `docker compose up` — `web` restarts in a loop

**Diagnose:** `docker compose logs web`
**Common causes:** `SECRET_KEY` unset (compose fails fast with
`?set SECRET_KEY in .env`), the db healthcheck never passing, or a migration
error.

---

## 2. Frontend cannot reach the backend

### Every request fails with a network error

**Diagnose:** DevTools → Network. Look at the actual request URL.
**Cause A:** the backend is not running → `curl http://localhost:8000/api/v1/health/`.
**Cause B:** `NEXT_PUBLIC_API_URL` is wrong.
**Look at:** `frontend/.env`, `frontend/src/config/env.ts`.

### It works locally but every call fails in Docker

**Cause:** `NEXT_PUBLIC_API_URL` was set to an internal service name such as
`http://web:8000/api/v1`. `NEXT_PUBLIC_*` values are **inlined into the browser
bundle at build time**, and `web` does not resolve in a user's browser.
**Look at:** `frontend/Dockerfile:24-27`, `docker-compose.yml:132-135`.
**Fix:** set it to a browser-reachable URL **and rebuild** — a restart is not
enough, the value is compiled in.

### CORS error: "No 'Access-Control-Allow-Origin' header"

**Cause:** the frontend origin is not in `CORS_ALLOWED_ORIGINS`.
**Look at:** `base.py:327`, `development.py:12-15`.
**Diagnose:**
```bash
curl -i -X OPTIONS http://localhost:8000/api/v1/tasks/ \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: GET"
```
Expect `access-control-allow-origin: http://localhost:3000`.
**Fix:** add the exact origin — scheme, host and port must match exactly.
`http://localhost:3000` and `http://127.0.0.1:3000` are different origins.
**Gotcha:** `CorsMiddleware` must stay high in `MIDDLEWARE`, above
`CommonMiddleware` (`base.py:90-91`).

---

## 3. Authentication

### Redirected to `/login` immediately after logging in

**Cause:** cookies were not set, or `/auth/me/` failed.
**Diagnose:**
1. DevTools → Application → Cookies → look for `nexora_refresh` (HttpOnly, on
   the API origin) and `nexora.session=1` (frontend origin). The access token is
   in memory and will **not** appear here — that is expected.
2. Network → check the `/auth/me/` response.
**Look at:** `token-storage.ts:37-40`, `auth-provider.tsx:36-56`.
**Common cause:** the login response did not contain `access`/`refresh` — check
`LoginView` and `EmailTokenObtainPairSerializer`.

### Logged out unexpectedly after ~15 minutes

**Cause:** the silent refresh failed. The access token is 15 minutes; the refresh
should extend it transparently.
**Diagnose:** Network → look for `POST /auth/refresh/`. Check its status.
**Possible reasons:**
- The refresh token was blacklisted (rotation used it elsewhere, or a password
  reset revoked everything).
- Multiple refreshes raced — but `refreshPromise` should prevent that
  (`client.ts:64-72`).
- The refresh cookie was cleared or expired (7 days).
**Look at:** `client.ts:41-72`, and `token_blacklist_blacklistedtoken` in the DB.

### 401 on every request even though I am logged in

**Diagnose:** check the `Authorization` header on a failing request.
- Header missing → `tokenStorage.getAccess()` returned null, so the cookie is
  gone or was never set.
- Header present but rejected → the token was signed with a different key.
  `SIGNING_KEY` falls back to `SECRET_KEY`; **changing `SECRET_KEY` invalidates
  every issued token.**

### Login returns 429

**Cause:** `LoginRateThrottle` — 10/min per IP.
**Look at:** `common/throttling.py:15-18`.
**Fix (dev):** raise `THROTTLE_LOGIN`, or flush the cache:
`python manage.py shell -c "from django.core.cache import cache; cache.clear()"`.
Tests already disable throttling via `config/settings/test.py`.

### The password-reset link does not work

**Diagnose:** look at the URL. If it contains `amp;token=` instead of `&token=`,
the text template rendered through an escaping engine.
**Look at:** `base.py:117-134` — the dedicated `"text"` engine with
`autoescape: False` exists precisely for this, and `common/email.py:51` selects
it with `using="text"`.
**Other causes:** the link expired (`PASSWORD_RESET_TIMEOUT`, 24h), or it was
already used — Django's token derives from the password hash and `last_login`, so
it self-invalidates.

---

## 4. Permissions

### 404 on an object I know exists

**This is by design.** `WorkspaceScopedViewSet.get_queryset()` filters by
membership, so a non-member's request finds nothing and DRF raises 404 rather
than 403.
**Diagnose:**
```sql
SELECT role FROM workspaces_workspacemember
WHERE workspace_id = '<ws>' AND user_id = '<user>';
```
No row means no access. **Fix:** add the membership.

### 403 "Only workspace owners, admins, and managers can review handovers"

**Cause:** your `WorkspaceMember.role` is `member`.
**Look at:** `handovers/views.py:40-45,87-90`, `REVIEWER_ROLES` in
`workspaces/models.py:25`.
**Note:** the sidebar hides the Reviews link for members
(`app-sidebar.tsx:71-74`), so if you can see the link but get 403, your role
changed after the page loaded — refresh.

### 403 "You are not a member of this workspace" when creating something

**Cause:** `_require_membership()` in `perform_create`.
**Frequent real cause:** `activeWorkspaceId` is stale after leaving a workspace.
Clear `localStorage["nexora.activeWorkspace"]` and reload.

---

## 5. Realtime notifications

### The bell badge only updates every 30 seconds

**That is the fallback working.** The socket is not connected, so
`useUnreadCount` polls (`hooks/use-notifications.ts:37`).
**Diagnose:** DevTools → Network → WS filter. Look for `/ws/notifications/`.

| What you see | Cause | Fix |
|---|---|---|
| No WS request at all | `enabled` false, or no `WebSocket` in the environment | Check the bell is mounted (it is in `(app)/layout.tsx`) |
| Connection refused | Backend running under WSGI, not ASGI | Use `runserver` (daphne) or uvicorn with `config.asgi:application` |
| 403 during handshake | `OriginValidator` rejected the Origin | Add the frontend origin to `CORS_ALLOWED_ORIGINS` — **not** `ALLOWED_HOSTS` |
| Closes with code 4401 | Token rejected by `JWTAuthMiddleware` | The access token expired between renders; it retries at 30s |
| Connects, then no messages | Channel layer mismatch across processes | Set `CHANNEL_LAYER_URL`/`REDIS_URL`; the in-memory layer is per-process |

**Look at:** `config/asgi.py:42-45`, `common/channels_auth.py`,
`notifications/consumers.py:35-45`, `hooks/use-notification-socket.ts`.

### Notifications arrive for some users but not others in production

**Almost certainly the channel layer.** With `InMemoryChannelLayer` and 3 uvicorn
workers, a notification created in worker A cannot reach a socket held by worker
B. `development.py:40-42` says this explicitly.
**Fix:** set `REDIS_URL` (or `CHANNEL_LAYER_URL`) so `channels_redis` is used.

---

## 6. Documents and embeddings

### `embedding_status` stays `pending` forever

**Diagnose:**
```sql
SELECT status, error, provider, model, started_at, finished_at
FROM knowledge_embeddingjob ORDER BY created_at DESC LIMIT 5;
```
**If `pending`:** the task was never picked up. Either no worker is running with
`CELERY_TASK_ALWAYS_EAGER=False`, or the broker is unreachable. The code falls
back to inline execution when `.delay()` throws
(`processor.py:47-52`) — so a stuck `pending` usually means the task **was**
queued and nothing is consuming it.
**If `failed`:** read the `error` column — it holds the exception text.

### `embedding_status` is `null`

**Cause:** no `EmbeddingJob` was ever created. Either the file extension is
unsupported (`extractor.SUPPORTED_EXTENSIONS`), or the document was created
without a file.
**Look at:** `knowledge/handlers.py:26-30` — unsupported types are skipped
**silently**, by design.

### The upload request hangs for a minute

**Cause:** `CELERY_TASK_ALWAYS_EAGER=True` (the development default), so
embedding runs inline — and the first run downloads a ~90 MB model from Hugging
Face.
**Fix:** wait for the first one, or run a real worker, or use
`seed_demo --skip-embedding`.

### AI search returns nothing for a document I can see

Check in order:

1. `SELECT COUNT(*) FROM knowledge_documentchunk WHERE document_id='<id>';`
   Zero → the document was never embedded.
2. `SELECT COUNT(*) FROM knowledge_documentchunk WHERE document_id='<id>' AND embedding IS NOT NULL;`
   Zero → chunks exist but were not embedded.
3. The distance cut-off: chunks further than `AI_SEARCH_MAX_DISTANCE` (0.75) are
   dropped entirely (`search.py:56`). A genuinely unrelated query returns `[]`.
4. Wrong workspace — retrieval is always workspace-filtered.
5. The file was a scanned PDF: `pypdf` extracts no text and there is **no OCR**.

### 503 "Semantic search isn't available yet"

**Cause:** a `DatabaseError` during retrieval, which almost always means the
pgvector extension or the migration is missing.
**Look at:** `ai/views.py:59-70` — this is a deliberate clean error instead of a
leaked 500.

---

## 7. AI chat

### 502 "Gemini API key is not configured for this workspace"

**Cause:** `get_llm_settings()` found no key — neither on the workspace's
`AISettings` nor in the environment fallback.
**Look at:** `ai/providers/factory.py:56-60`, `providers/gemini.py:14-17`.
**Fix:** set `GEMINI_API_KEY`, or add a per-workspace key at `/ai/settings`.

### 502 with a provider error message

The upstream LLM failed. Every provider wraps its exception in `ProviderError`
and the view maps it to 502 — semantically correct, since the failure is
upstream, not here.

### 429 on AI endpoints

`AIRateThrottle` — 30/hour per user, because LLM calls cost money.
Raise `THROTTLE_AI` if needed.

### "AI is disabled for this workspace"

`AISettings.is_enabled = False`. Turn it on at `/ai/settings` (owner/admin only).

### The chat answers with generic knowledge instead of my documents

Check `confidence` in the response. `low` means the top retrieval score was under
0.4, so the model had little to work with. The guardrails instruct it to say it
does not have enough information — a model that ignores that is doing so despite
the prompt. Check that the relevant document actually has chunks.

---

## 8. Database

### `connection already closed` / `too many connections`

**Cause:** no connection pooling. `CONN_MAX_AGE` is unset (verified), so every
request opens a new connection, and `max_connections` becomes the ceiling.
**Diagnose:** `SELECT count(*) FROM pg_stat_activity;`
**Fix:** set `CONN_MAX_AGE = 60`, or put PgBouncer in front. See
[19-performance-scalability.md](19-performance-scalability.md).

### `IntegrityError: duplicate key value violates unique constraint`

Which constraint tells you what happened:

| Constraint | Meaning |
|---|---|
| `unique_workspace_member` | Tried to add someone twice — `get_or_create` in the accept path is the correct pattern |
| `unique_project_slug_per_workspace` | The slug check-then-act race (see [14-algorithms.md](14-algorithms.md#7-unique-slug-generation)) |
| `accounts_user_email_key` | Registration race, or a case-mismatch bypass of `validate_email` |
| `unique_document_chunk_index` | Two embedding jobs for one document ran concurrently |

### A page shows stale data after an update

**Cause:** the mutation did not invalidate the right query key.
**Look at:** the `onSuccess` in the relevant `hooks/use-*.ts`.
**Diagnose:** open React Query Devtools (already mounted in dev) and inspect the
key. Cross-module writes need extra invalidation — `use-handovers.ts:73` also
invalidates `["tasks"]` because approval reassigns a task.

### An audit entry is missing

**Cause:** the write bypassed `post_save`. `queryset.update()`, `bulk_create()`,
raw SQL and direct psql edits fire **no signals**, so nothing is logged.
**Look at:** `activities/handlers.py` for the list of registered models. Note
`NotificationViewSet.read_all` uses `.update()` deliberately.

---

## 9. Build and tooling

### `pnpm install` complains about the lockfile

The lockfile is pnpm's. npm and yarn will not match it. CI runs
`pnpm install --frozen-lockfile`, which **fails rather than silently updating**.

### `pnpm typecheck` fails after a backend change

Expected, and the point. The types in `frontend/src/types/` are hand-written
mirrors of the DRF serializers. Change a serializer field and the frontend
compile catches the drift.

### CI fails on "Fail if a model change has no migration"

`makemigrations --check --dry-run` found an unmigrated model change.
**Fix:** `python manage.py makemigrations` and commit the file.

### CI fails on `manage.py check --fail-level WARNING`

Warnings are treated as errors. Read the check id in the output; Django's
messages name the exact setting.

### Tests fail with 429

You are not running under `config.settings.test`, which sets every throttle rate
to `None`. `manage.py test` selects it automatically — check you are not
overriding `DJANGO_SETTINGS_MODULE`.

---

## 10. A general debugging method for this codebase

When a page shows the wrong thing:

1. **Reproduce**, and note the exact workspace and user.
2. **Frontend state** — React Query Devtools: which key, what data, is it stale?
3. **Network** — is the request even sent? What params? What status?
4. **API response** — is the data wrong, or is the rendering wrong? Replay the
   request in `/api/docs/` as the same user.
5. **View** — read `get_queryset()`. Nearly every "missing data" bug in this
   codebase is a scoping filter.
6. **Serializer** — is the field a `SerializerMethodField` computing something
   unexpected?
7. **SQL** — `django-debug-toolbar` is not installed, so use
   `python manage.py shell` and `print(qs.query)`, or
   `django.db.connection.queries` after a request.
8. **Database** — query the table directly and compare.
9. **Signals** — if data is missing that should have been created as a side
   effect, check whether the write path fires `post_save` at all.
10. **Fix, then add a regression test** — the backend suite is the right place;
    see [26-testing.md](26-testing.md).

---

**Next:** [24 — Technical Decisions](24-technical-decisions.md)
