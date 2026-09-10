# API — Core (Health, Dashboard, Analytics) & Activities

[← API index](README.md) · [Module deep dive](../modules/dashboard-analytics.md) ·
[Audit module](../modules/activity-audit.md)

`backend/apps/core/views.py` · `backend/apps/activities/views.py`

---

## `GET /api/v1/health/`

**The only fully public endpoint in the API.**

```python
permission_classes = [AllowAny]
authentication_classes: list = []       # ← no auth machinery at all
```

Both are set: `AllowAny` skips permission checks, and the empty
`authentication_classes` means a malformed `Authorization` header cannot make the
health check fail.

**Response `200`**
```json
{ "status": "ok", "service": "ai-knowledge-workflow-assistant",
  "version": "v1", "database": "ok" }
```

**Response `503`**
```json
{ "status": "degraded", "service": "...", "version": "v1", "database": "unavailable" }
```

The check itself is `connection.ensure_connection()` in a `try`.

Public on purpose, per the docstring, so uptime monitors and orchestrators can
reach it without a token. It is the `web` service's Docker healthcheck:

```yaml
test: ["CMD", "curl", "-fsS", "http://localhost:8000/api/v1/health/"]
```

---

## `GET /api/v1/dashboard/?workspace=<uuid>`

**Auth:** member. `?workspace=` is **required**.

```python
workspace_id = request.query_params.get("workspace")
if not workspace_id:
    raise ValidationError({"workspace": "This query parameter is required."})
workspace = get_object_or_404(
    Workspace.objects.filter(members__user=request.user).distinct(), pk=workspace_id)
```

The membership filter is **inside** `get_object_or_404`, so a non-member gets
**404**, not 403.

**Response `200`**

```json
{
  "stats": {
    "total_projects": 12, "active_projects": 5, "archived_projects": 2,
    "total_tasks": 61, "pending_tasks": 34, "completed_tasks": 21,
    "overdue_tasks": 4, "total_documents": 9,
    "my_tasks": 7, "pending_handovers": 3
  },
  "recent_projects":   [ /* 5 × ProjectSerializer */ ],
  "recent_tasks":      [ /* 5 × TaskSerializer */ ],
  "recent_documents":  [ /* 5 × DocumentSerializer */ ],
  "pending_handovers": [ /* 5 × HandoverSerializer */ ]
}
```

### Stat definitions — memorise these

```python
OPEN_TASK_STATUSES = (TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.REVIEW)
```

| Stat | Definition |
|---|---|
| `active_projects` | `status=active` **and** `archived=False` |
| `pending_tasks` | status in `OPEN_TASK_STATUSES` |
| `completed_tasks` | `status=completed` |
| `overdue_tasks` | **open and `due_date < today`** — a completed task with a past due date is not overdue |
| `my_tasks` | open **and** `assignee = request.user` |
| `pending_handovers` | `status=pending` **workspace-wide** — not filtered to ones you can review |

### Cost

**15+ queries per request** — ten `.count()` calls plus four list queries, and
`DocumentSerializer` adds two more per document row. This is the first screen
every user loads. Fix in
[19-performance-scalability.md](../19-performance-scalability.md#-23-the-dashboard-fires-15-queries).

---

## `GET /api/v1/analytics/?workspace=<uuid>`

**Auth:** member. `?workspace=` required, same 404 behaviour via
`_workspace_or_404`.

**Response `200`**

```json
{
  "task_status":   [ { "status": "todo", "count": 12 }, ... ],
  "task_priority": [ { "priority": "high", "count": 8 }, ... ],
  "weekly": [
    { "week_start": "2026-07-20", "created": 6, "completed": 4 },
    ... 8 entries, oldest first ...
  ],
  "workload": [
    { "user_id": "<uuid>", "name": "Asha Rao", "count": 9 }, ... up to 8 ...
  ],
  "handovers": {
    "pending": 3, "approved": 11, "rejected": 2, "avg_review_hours": 6.4
  }
}
```

### Definitions

| Key | How it is computed |
|---|---|
| `task_status` | `values("status").annotate(count=Count("id"))` |
| `task_priority` | same on `priority` |
| `weekly` | Last **8 ISO weeks**, Monday-based, oldest first. Buckets pre-seeded so quiet weeks appear as zeros |
| `weekly[].created` | Tasks whose `created_at` falls in that week |
| `weekly[].completed` | Tasks with `status=completed` whose **`updated_at`** falls in that week |
| `workload` | Top 8 assignees by count of **open** tasks; `name` falls back to email |
| `handovers.avg_review_hours` | `Avg(F("reviewed_at") - F("created_at"))` over reviewed handovers, in hours, 1dp. **`null` when none have been reviewed** |

### The documented approximation

The view's own docstring:

> "Completed" per week counts tasks whose status is completed by their last
> update in that week (the model has no dedicated `completed_at` column).

So editing a task completed months ago moves it into the current week's bar. Fix:
add `completed_at`. See [25-known-limitations.md](../25-known-limitations.md).

### The interval arithmetic

```python
reviewed.annotate(wait=F("reviewed_at") - F("created_at")).aggregate(avg=Avg("wait"))
```

The subtraction and the average both happen **in PostgreSQL**, using its native
`interval` type — not in Python. Only the `/3600` rounding is done in Django.

The frontend must handle `avg_review_hours: null`.

---

## Activities — `/api/v1/activities/`

`ActivityViewSet(viewsets.ReadOnlyModelViewSet)` — **list and retrieve only**.
There is no way to write an activity row through the API.

### `GET /activities/`

**Scope:** `filter(workspace__members__user=self.request.user).distinct()`
with `select_related("actor", "content_type")`.

**Filters** — hand-rolled in `get_queryset`, not django-filter:

| Param | Maps to |
|---|---|
| `workspace` | `workspace_id` |
| `action` | exact, e.g. `task.created` |
| `actor` | `actor_id` |
| `date_from` | `created_at__date__gte` |
| `date_to` | `created_at__date__lte` |
| `target_type` | `content_type__model`, e.g. `task` |
| `target_id` | `object_id` — used for per-object timelines |

**Response** — paginated `ActivitySerializer`:

```json
{ "id": "<uuid>",
  "actor": { ...UserSerializer... },
  "action": "task.updated",
  "target_type": "task",
  "object_id": "<uuid>",
  "metadata": { "title": "Fix billing sync", "status": "in_progress" },
  "workspace": "<uuid>",
  "created_at": "..." }
```

`target_type` is a `SerializerMethodField` returning `content_type.model`, or
`null`. **Delete rows have `target_type: null` and `object_id: null`** — the
object is gone, which is exactly why `metadata` carries a snapshot.

`?target_type=task&target_id=<uuid>` is what powers the per-object timeline in
`components/comments/collaboration-tabs.tsx`.

### Known action values

`project.created` `.updated` `.deleted` · `task.*` · `document.*` ·
`handover.*` · `comment.created` · `workspace.created` `.updated` ·
`member.*` · `member.invited`

`lib/activity.ts` on the frontend maps these to labels and icons.

### `GET /activities/export/`

**Response `200 text/csv`**, header
`Content-Disposition: attachment; filename="audit-log.csv"`

```
timestamp,actor,action,target_type,target_id,metadata
2026-09-10T09:14:22+00:00,Asha Rao,task.created,task,<uuid>,"{'title': '...', 'status': 'todo'}"
```

```python
for activity in self.get_queryset()[:EXPORT_LIMIT]:      # 10_000
```

Two properties: it reuses `get_queryset()`, so **the export respects the current
filters**; and `EXPORT_LIMIT = 10_000` bounds the response — *"to keep the
response bounded."*

Fetched by `lib/api/download.ts`, not `apiClient` (which parses JSON).

**Improvement:** `StreamingHttpResponse` + `.iterator()` — see
[19](../19-performance-scalability.md).

---

## Frontend consumption

| Endpoint | Hook | Page |
|---|---|---|
| `/health/` | `useHealth()` | not surfaced in the UI |
| `/dashboard/` | `useDashboard(workspaceId)` | `/dashboard` |
| `/analytics/` | `useAnalytics(workspaceId)` | `/analytics` |
| `/activities/` | `useActivities(params)` | `/activity` + detail-page timelines |
| `/activities/export/` | `downloadFile(...)` | `/activity` export button |

---

## Errors

| Status | When |
|---|---|
| `400 {"workspace": ["This query parameter is required."]}` | `?workspace=` omitted from dashboard or analytics |
| `404` | Workspace does not exist, **or** you are not a member — indistinguishable by design |
| `503` | `/health/` only, when the database is unreachable |
| `500` | Dashboard/analytics when the database is down |
