# 07 — API Architecture

[← Back to index](README.md)

Endpoint-by-endpoint reference lives in [`api/`](api/README.md). This file
documents the **conventions** every endpoint follows.

---

## 1. Shape of the API

- **Style:** REST over JSON, one version prefix: `/api/v1/`.
- **Auth:** `Authorization: Bearer <access-token>`. No cookies, no sessions.
- **Content type:** `application/json`, except document upload which is
  `multipart/form-data`, and two binary responses (`application/pdf`, `text/csv`).
- **Trailing slashes are required.** DRF's `DefaultRouter` generates
  `/tasks/` and `/tasks/{id}/`. Every path in `API_ROUTES` ends with `/`.
- **IDs are UUIDs** everywhere except invitations, which are keyed by their
  `token` string (`lookup_field = "token"`, `apps/invitations/views.py:37`).
- **Schema:** OpenAPI 3 at `/api/schema/`, Swagger UI at `/api/docs/`, ReDoc at
  `/api/redoc/`.

---

## 2. Full endpoint inventory

| Area | Endpoints |
|---|---|
| Health | `GET /health/` (public, no auth class at all) |
| Auth | `POST /auth/register/` · `/auth/login/` · `/auth/refresh/` · `/auth/logout/` · `GET`/`PATCH /auth/me/` |
| Password reset | `POST /auth/password-reset/` · `POST /auth/password-reset/confirm/` |
| Workspaces | `GET/POST /workspaces/` · `GET/PUT/PATCH/DELETE /workspaces/{id}/` · `GET /workspaces/{id}/members/` · `PATCH/DELETE /workspaces/{id}/members/{member_id}` · `POST /workspaces/{id}/transfer-ownership/` |
| Projects | CRUD `/projects/` · `POST /projects/{id}/archive/` · `POST /projects/{id}/restore/` |
| Tasks | CRUD `/tasks/` |
| Handovers | CRUD `/handovers/` · `POST /handovers/{id}/review/` · `GET /handovers/{id}/export/` (PDF) |
| Documents | CRUD `/documents/` (multipart create) · `POST /documents/{id}/reindex/` |
| Comments | CRUD `/comments/` · `POST /comments/{id}/reply/` |
| Mentions | `GET /mentions/` · `GET /mentions/{id}/` (read-only) |
| Notifications | `GET /notifications/` · `GET /notifications/{id}/` · `PATCH /notifications/{id}/read/` · `PATCH /notifications/read-all/` · `GET /notifications/unread-count/` |
| Activities | `GET /activities/` · `GET /activities/{id}/` · `GET /activities/export/` (CSV) |
| Invitations | `GET/POST /invitations/` · `GET/DELETE /invitations/{token}/` · `POST /invitations/{token}/accept/` · `/reject/` · `/resend/` |
| Dashboard | `GET /dashboard/?workspace=` |
| Analytics | `GET /analytics/?workspace=` |
| AI actions | `POST /ai/chat/` · `/ai/search/` · `/ai/summarize/` · `/ai/generate-tasks/` |
| AI settings | `GET`/`PATCH /ai/settings/` |
| AI resources | `/ai/conversations/` (list/retrieve/delete) · `/ai/search-history/` (list) · `/ai/prompt-templates/` (CRUD) |
| Realtime | `WS /ws/notifications/?token=<access>` |

> `PUT` exists on every `ModelViewSet` but the frontend only ever sends `PATCH`
> for updates. `InvitationViewSet` explicitly restricts methods:
> `http_method_names = ["get", "post", "delete", "head", "options"]`.

---

## 3. Response conventions

### Paginated list

Every list endpoint returns DRF's `PageNumberPagination` envelope, page size 20:

```json
{
  "count": 137,
  "next": "http://localhost:8000/api/v1/tasks/?page=3",
  "previous": "http://localhost:8000/api/v1/tasks/?page=1",
  "results": [ ... ]
}
```

The frontend types this once as `Paginated<T>` (`frontend/src/types/index.ts:7-12`)
and `PAGE_SIZE = 20` is mirrored in `lib/constants.ts:180`.

### Detail

A bare object, no envelope.

### Errors

DRF's default shapes, which `lib/api/client.ts` normalises into one `ApiError`:

| Status | Body | Produced by |
|---|---|---|
| 400 | `{"field": ["message"], ...}` or `{"detail": "..."}` | serializer `ValidationError` |
| 401 | `{"detail": "Given token not valid for any token type", ...}` | SimpleJWT |
| 403 | `{"detail": "<permission .message>"}` | permission class or `PermissionDenied` |
| 404 | `{"detail": "No Task matches the given query."}` | queryset filtering |
| 405 | `{"detail": "Method \"PUT\" not allowed."}` | `http_method_names` |
| 429 | `{"detail": "Request was throttled. Expected available in N seconds."}` | throttle |
| 500 | HTML (DEBUG) or `{"detail": "..."}`| unhandled exception |
| 502 | `{"detail": "<provider message>"}` | `_provider_error_response`, `ai/views.py:53-56` |
| 503 | `{"detail": "Semantic search isn't available yet..."}` | `_retrieval_unavailable_response`, `ai/views.py:59-70` |

Client-side normalisation:

```ts
const error: ApiError = {
  status: response.status,
  message: (data && (data.detail || data.message)) || response.statusText || "Request failed",
  details: data && typeof data === "object" ? data : undefined,
};
throw error;
```
`frontend/src/lib/api/client.ts:117-125`

`details` keeps the raw body so `applyFieldErrors()` can map field errors onto
form inputs.

---

## 4. Filtering, searching, ordering, pagination

All four are supplied by the DRF backends configured globally
(`config/settings/base.py:191-197`). Each scoped viewset then declares what it
supports.

| Resource | FilterSet fields | `search_fields` | `ordering_fields` |
|---|---|---|---|
| Projects | `workspace`, `status`, `archived`, `owner` | `name`, `description` | `created_at`, `updated_at`, `name`, `status` |
| Tasks | `workspace`, `project`, `status`, `priority`, `assignee`, plus `due_before` / `due_after` | `title`, `description` | `created_at`, `updated_at`, `due_date`, `priority`, `status`, `title` |
| Documents | `workspace`, `project`, `file_type` (`exact`, `icontains`) | `title`, `description` | `created_at`, `updated_at`, `title`, `file_size` |
| Handovers | `workspace`, `task`, `status`, `from_user`, `to_user`, plus `project` (→ `task__project_id`) | `summary`, `pending_items`, `task__title` | `created_at`, `updated_at`, `status`, `reviewed_at` |
| Prompt templates | `workspace`, `category` | `name`, `description` | `name`, `created_at` |

`due_before` / `due_after` and `project` are **custom filters** — declared
explicitly because the model has no such field:

```python
due_before = django_filters.DateFilter(field_name="due_date", lookup_expr="lte")
due_after  = django_filters.DateFilter(field_name="due_date", lookup_expr="gte")
```
`backend/apps/tasks/filters.py:9-10`

```python
project = django_filters.UUIDFilter(field_name="task__project_id")
```
`backend/apps/handovers/filters.py:9`

Four resources do **not** use `django-filter` and hand-roll query-param filtering
in `get_queryset()` instead: comments, notifications, activities, invitations.
That is a deliberate choice where the filter is not a simple model field —
`ActivityViewSet` for instance supports `date_from`, `date_to`, `target_type` and
`target_id` (`apps/activities/views.py:41-55`).

Query-string building on the client drops empty values, so `?status=` never
appears:

```ts
if (value !== undefined && value !== null && value !== "") search.append(key, String(value));
```
`frontend/src/lib/api/client.ts:31-33`

---

## 5. Rate limiting

`config/settings/base.py:203-217`, classes in `apps/common/throttling.py`.

| Scope | Default rate | Keyed by | Applied to |
|---|---|---|---|
| `anon` | 60/min | IP | every unauthenticated request |
| `user` | 1000/hour | user id | every authenticated request |
| `login` | 10/min | **IP** | `LoginView` |
| `register` | 5/hour | **IP** | `RegisterView` |
| `password_reset` | 5/hour | **IP** | both password-reset views |
| `ai` | 30/hour | user id (IP if anonymous) | `ChatView`, `SearchView`, `SummarizeView`, `GenerateTasksView` |

Every rate is overridable by environment variable
(`THROTTLE_LOGIN`, `THROTTLE_AI`, …).

Two reasoning notes taken straight from the code comments:

- Credential endpoints are keyed by **IP, not user**, because the whole point is
  to limit an attacker who has no valid account yet and would otherwise get a
  fresh bucket per guessed email (`throttling.py:7-9`).
- `PasswordResetRateThrottle` deliberately does **not** key on the submitted
  email address — that would let an attacker lock a specific person out of
  password resets (`throttling.py:29-32`).

Counters live in the Django cache, which is Redis in production. `base.py:222-226`
explains why that matters: with the default per-process `LocMemCache`, each
gunicorn/uvicorn worker keeps a private counter, so the effective limit becomes
`rate × worker_count`.

---

## 6. Two endpoint families that break the CRUD mould

### a. Aggregate endpoints — workspace in the query string

`GET /dashboard/?workspace=<id>` and `GET /analytics/?workspace=<id>` are
`APIView`s, not viewsets. Both start with the same guard:

```python
workspace = get_object_or_404(
    Workspace.objects.filter(members__user=request.user).distinct(),
    pk=workspace_id,
)
```
`backend/apps/core/views.py:98-101`

Note the filter is *inside* `get_object_or_404`. A non-member gets **404**, not
403 — the same "don't confirm the id exists" property as the scoped viewsets.

### b. AI action endpoints — workspace in the body

`POST /ai/chat/`, `/ai/search/`, `/ai/summarize/`, `/ai/generate-tasks/` all take
`{"workspace": "<uuid>", ...}` in the JSON body, so DRF object permissions cannot
be used. They call `resolve_workspace()` first:

```python
def resolve_workspace(user, workspace_id, *, require_admin: bool = False):
    workspace = Workspace.objects.filter(pk=workspace_id).first()
    if workspace is None:                       raise NotFound(...)
    member = workspace.members.filter(user=user).first()
    if member is None:                          raise PermissionDenied(...)
    if require_admin and member.role not in (OWNER, ADMIN):  raise PermissionDenied(...)
    return workspace
```
`backend/apps/ai/permissions.py:15-33`

**Every AI endpoint calls this before any retrieval happens.** That single
function is the tenant isolation gate for the entire AI surface.

> Behaviour difference worth noting: this returns **404** for a nonexistent
> workspace and **403** for a workspace you are not in — so it *does* reveal
> whether a workspace id exists. The rest of the API returns 404 for both.
> Recorded in [18-security.md](18-security.md).

---

## 7. Binary responses

Two endpoints return files, and neither can go through `apiClient` (which parses
JSON):

| Endpoint | Content type | Produced by |
|---|---|---|
| `GET /handovers/{id}/export/` | `application/pdf` | `apps/handovers/pdf.py` via reportlab |
| `GET /activities/export/` | `text/csv` | `csv.writer` into an `HttpResponse`, capped at `EXPORT_LIMIT = 10_000` rows |

Both set `Content-Disposition: attachment; filename="..."`. The client uses a
separate helper that fetches with the bearer token, reads the blob, and triggers
a download, preferring the server-provided filename:

```ts
const disposition = response.headers.get("Content-Disposition") ?? "";
const match = /filename="?([^";]+)"?/.exec(disposition);
const filename = match?.[1] ?? fallbackName;
```
`frontend/src/lib/api/download.ts:28-30`

`downloadFile` does **not** implement token refresh. If the access token has
expired at the moment of download, the export fails with a toast rather than
retrying. Minor, listed in [25-known-limitations.md](25-known-limitations.md).

---

## 8. The full call chain, template

Every endpoint in [`api/`](api/README.md) is documented in this shape:

```
Frontend action        button / form submit
        ↓
Hook                   hooks/use-x.ts  (TanStack Query)
        ↓
API service            lib/api/x.ts
        ↓
Transport              lib/api/client.ts   (+ JWT, refresh, error normalisation)
        ↓ HTTP
Django URLconf         config/urls.py → apps/x/urls.py
        ↓
View                   apps/x/views.py
        ↓
Permission             apps/common/permissions.py / inline check
        ↓
Serializer             apps/x/serializers.py  (validate)
        ↓
Model / ORM            apps/x/models.py
        ↓
PostgreSQL             table(s)
        ↓
Signals                apps/*/handlers.py   (audit, notify, embed)
        ↓
Response               serializer → JSON
        ↓
Cache                  TanStack Query stores/invalidates
        ↓
UI                     re-render
```

Worked examples: [11-data-flow.md](11-data-flow.md).

---

## 9. API design decisions worth defending

| Decision | Where | Rationale in the code |
|---|---|---|
| Version prefix from day one | `config/urls.py:37` | "so new versions can be added side-by-side later" |
| UUID ids | `apps/common/models.py:27` | "safe to expose in URLs/APIs" |
| `IsAuthenticated` as the global default | `base.py:188-190` | New endpoints are private unless someone deliberately opens them |
| 404 instead of 403 for cross-tenant reads | `common/viewsets.py:30-33` | Does not confirm the id exists |
| Workspace derived from parent, not client-supplied | `tasks/serializers.py:76`, `handovers/serializers.py:86` | Cannot mismatch a task's project and workspace |
| Invitations keyed by token, not id | `invitations/views.py:37` | The token *is* the credential; the URL doubles as the accept link |
| Socket is push-only | `notifications/consumers.py:8-9` | "keeps one code path for permissions and auditing" |
| AI endpoints are POST, even search | `ai/urls.py` | Queries can be long and are logged to `SearchHistory`; also keeps them off URLs/logs |

---

**Next:** [08 — Authentication & Authorization](08-authentication-authorization.md)
