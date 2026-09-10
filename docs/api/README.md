# API Reference

[← Docs index](../README.md) · [Conventions](../07-api-architecture.md)

Base URL: `/api/v1/` · Auth: `Authorization: Bearer <access token>` ·
Live schema: `/api/schema/`, Swagger at `/api/docs/`, ReDoc at `/api/redoc/`

---

## Files

| File | Covers |
|---|---|
| [authentication.md](authentication.md) | register · login · refresh · logout · me · password reset |
| [workspaces.md](workspaces.md) | workspaces · members · transfer-ownership · invitations |
| [projects-tasks.md](projects-tasks.md) | projects (+ archive/restore) · tasks |
| [handovers.md](handovers.md) | handovers · review · PDF export |
| [documents.md](documents.md) | documents (multipart upload) · reindex |
| [collaboration.md](collaboration.md) | comments · mentions · notifications · websocket |
| [ai.md](ai.md) | chat · search · summarize · generate-tasks · settings · conversations · templates |
| [core.md](core.md) | health · dashboard · analytics · activities (+ CSV export) |

---

## Universal conventions

**Trailing slashes are required.** `/tasks/` and `/tasks/{id}/`.

**IDs are UUIDs**, except invitations which are keyed by their `token`.

**Every list response** uses DRF `PageNumberPagination`, page size 20:

```json
{ "count": 137, "next": "...?page=3", "previous": "...?page=1", "results": [ ... ] }
```

**Every list endpoint** supports `?search=`, `?ordering=` (prefix `-` to reverse)
and `?page=`, plus its own FilterSet fields.

**Every error** is normalised client-side into
`{status, message, details}` by `frontend/src/lib/api/client.ts`.

| Status | Meaning here |
|---|---|
| 400 | Validation — body is `{field: ["msg"]}` or `{"detail": "..."}` |
| 401 | Missing/expired token. The client refreshes once and retries automatically |
| 403 | Authenticated but not permitted — the message says why |
| 404 | Not found **or not in a workspace you belong to** (the two are indistinguishable, by design) |
| 405 | Method not allowed |
| 429 | Throttled |
| 502 | Upstream LLM provider failed |
| 503 | Vector store unavailable, or database down (health check) |

---

## Complete endpoint index

### Auth — `/api/v1/auth/`

| Method | Path | Auth | Throttle |
|---|---|---|---|
| POST | `register/` | public | 5/hour by IP |
| POST | `login/` | public | 10/min by IP |
| POST | `refresh/` | public (needs a valid refresh token) | default |
| POST | `logout/` | required | default |
| GET | `me/` | required | default |
| PATCH | `me/` | required | default |
| POST | `password-reset/` | public | 5/hour by IP |
| POST | `password-reset/confirm/` | public | 5/hour by IP |

### Workspaces — `/api/v1/workspaces/`

| Method | Path | Who |
|---|---|---|
| GET/POST | `/` | authenticated |
| GET | `{id}/` | member |
| PATCH/PUT | `{id}/` | owner/admin |
| DELETE | `{id}/` | **owner** |
| GET | `{id}/members/` | member |
| PATCH/DELETE | `{id}/members/{member_id}` | owner/admin |
| POST | `{id}/transfer-ownership/` | **owner** |

### Invitations — `/api/v1/invitations/`

| Method | Path | Who |
|---|---|---|
| GET | `/` | mine, or workspaces I administer |
| POST | `/` | owner/admin |
| GET | `{token}/` | scoped audience |
| DELETE | `{token}/` | owner/admin (→ `cancelled`) |
| POST | `{token}/accept/` | the invited email |
| POST | `{token}/reject/` | the invited email |
| POST | `{token}/resend/` | owner/admin |

### Projects — `/api/v1/projects/`

| Method | Path |
|---|---|
| GET/POST | `/` |
| GET/PATCH/PUT/DELETE | `{id}/` |
| POST | `{id}/archive/` |
| POST | `{id}/restore/` |

Filters: `workspace` `status` `archived` `owner`

### Tasks — `/api/v1/tasks/`

| Method | Path |
|---|---|
| GET/POST | `/` |
| GET/PATCH/PUT/DELETE | `{id}/` |

Filters: `workspace` `project` `status` `priority` `assignee` `due_before` `due_after`

### Handovers — `/api/v1/handovers/`

| Method | Path | Who |
|---|---|---|
| GET/POST | `/` | member |
| GET | `{id}/` | member |
| PATCH | `{id}/` | submitter, pending only |
| DELETE | `{id}/` | submitter or reviewer, pending only |
| POST | `{id}/review/` | **owner/admin/manager** |
| GET | `{id}/export/` | member → `application/pdf` |

Filters: `workspace` `task` `project` `status` `from_user` `to_user`

### Documents — `/api/v1/documents/`

| Method | Path | Notes |
|---|---|---|
| GET | `/` | Filters: `workspace` `project` `file_type` |
| POST | `/` | **multipart/form-data** |
| GET/PATCH/DELETE | `{id}/` | PATCH is metadata-only |
| POST | `{id}/reindex/` | → 202 |

### Comments — `/api/v1/comments/`

| Method | Path | Who |
|---|---|---|
| GET | `/?target_type=&target_id=` | member |
| POST | `/` | member |
| PATCH | `{id}/` | **author** |
| DELETE | `{id}/` | author or workspace owner/admin (soft) |
| POST | `{id}/reply/` | member |

### Mentions — `/api/v1/mentions/`

| Method | Path |
|---|---|
| GET | `/?workspace=` — read-only, only where you are mentioned |
| GET | `{id}/` |

### Notifications — `/api/v1/notifications/`

| Method | Path |
|---|---|
| GET | `/?is_read=&type=&workspace=` |
| GET | `{id}/` |
| PATCH | `{id}/read/` |
| PATCH | `read-all/` |
| GET | `unread-count/` |

### Activities — `/api/v1/activities/`

| Method | Path |
|---|---|
| GET | `/?workspace=&action=&actor=&date_from=&date_to=&target_type=&target_id=` |
| GET | `{id}/` |
| GET | `export/` → `text/csv`, capped at 10,000 rows |

### AI — `/api/v1/ai/`

| Method | Path | Throttle |
|---|---|---|
| POST | `chat/` | 30/hour per user |
| POST | `search/` | 30/hour |
| POST | `summarize/` | 30/hour |
| POST | `generate-tasks/` | 30/hour |
| GET/PATCH | `settings/` | default (PATCH needs owner/admin) |
| GET/DELETE | `conversations/`, `conversations/{id}/` | default |
| GET | `search-history/` | default |
| GET/POST/PATCH/DELETE | `prompt-templates/`, `prompt-templates/{id}/` | default |

### Core

| Method | Path | Auth |
|---|---|---|
| GET | `health/` | **public** |
| GET | `dashboard/?workspace=` | member |
| GET | `analytics/?workspace=` | member |

### Realtime

| Protocol | Path |
|---|---|
| WS | `/ws/notifications/?token=<access>` — push-only |

---

## The call chain, for every endpoint

```
page.tsx  →  hooks/use-*.ts  →  lib/api/*.ts  →  lib/api/client.ts
    → HTTP →
config/urls.py → apps/<x>/urls.py → views.py → permission → serializer → model → PostgreSQL
    → signals (audit, notify, embed) →
JSON → TanStack Query cache → re-render
```

Worked traces: [11-data-flow.md](../11-data-flow.md).
