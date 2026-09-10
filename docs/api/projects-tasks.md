# API — Projects & Tasks

[← API index](README.md) · [Module deep dive](../modules/projects-tasks.md)

Both are `WorkspaceScopedViewSet` subclasses, so both inherit:

- `permission_classes = [IsAuthenticated, IsWorkspaceMember]`
- queryset filtered by `workspace__members__user=request.user` → **404** for
  another tenant's row
- `perform_create` membership check + `created_by`/`updated_by` stamping
- `perform_update` `updated_by` stamping
- pagination (20), `?search=`, `?ordering=`

---

# Projects — `/api/v1/projects/`

## `GET /projects/`

**Filters** (`ProjectFilter`): `workspace` · `status` · `archived` · `owner`
**Search:** `name`, `description`
**Ordering:** `created_at`, `updated_at`, `name`, `status` (default `-created_at`)

**Response** — paginated `ProjectSerializer`:

```json
{ "id": "<uuid>", "workspace": "<uuid>",
  "name": "Billing v2", "slug": "billing-v2", "description": "",
  "color": "#6366f1", "status": "active", "archived": false,
  "owner": { ...UserSerializer... },
  "task_count": 14,
  "created_by": { ... }, "updated_by": { ... },
  "created_at": "...", "updated_at": "..." }
```

Read-only: `id`, `slug`, `owner`, `created_by`, `updated_by`, timestamps.

> `task_count` uses `source="tasks.count"` — one extra query per row. See
> [19](../19-performance-scalability.md).

## `POST /projects/`

**Request** `{ "workspace": "<uuid>", "name": "Billing v2", "description": "",
"color": "#6366f1", "status": "planning" }`

- `workspace` **is** required here (unlike Task, where it is derived) and is
  membership-checked by `_require_membership`.
- `slug` is generated and de-duplicated **per workspace**
  (`unique_project_slug_per_workspace`).
- `owner` defaults to the requesting user (`ProjectSerializer.create:41-46`).

**Response `201`.** Fires `project.created` in the audit log.

## `PATCH /projects/{id}/` · `DELETE /projects/{id}/`

PATCH stamps `updated_by`. DELETE **cascades to all tasks**; documents survive
with `project = NULL`.

## `POST /projects/{id}/archive/` and `/restore/`

```python
def _set_archived(self, request, archived: bool):
    project = self.get_object()
    project.archived = archived
    project.updated_by = request.user
    project.save(update_fields=["archived","updated_by","updated_at"])
    return Response(self.get_serializer(project).data)
```

Both take no body and return `200` with the updated project.

**Why an action rather than `PATCH {archived: true}`:** it expresses a distinct,
auditable intent and gives the frontend a single-purpose endpoint. One
implementation serves both.

Note the audit row is `project.updated` with `metadata.archived`, **not** a
dedicated `project.archived` action — the archive path goes through `save()`.

---

# Tasks — `/api/v1/tasks/`

## `GET /tasks/`

**Filters** (`TaskFilter`):

| Param | Lookup |
|---|---|
| `workspace` | exact |
| `project` | exact |
| `status` | `todo` / `in_progress` / `review` / `completed` / `cancelled` |
| `priority` | `low` / `medium` / `high` / `critical` |
| `assignee` | exact (user id) |
| `due_before` | `due_date__lte` — **custom** |
| `due_after` | `due_date__gte` — **custom** |

**Search:** `title`, `description`
**Ordering:** `created_at`, `updated_at`, `due_date`, `priority`, `status`, `title`

> `priority` orders **alphabetically**, not by severity — `critical`, `high`,
> `low`, `medium`. The enum stores strings. A severity sort would need a
> `Case`/`When` annotation or an integer column.

**Response** — paginated `TaskSerializer`:

```json
{ "id": "<uuid>", "workspace": "<uuid>", "project": "<uuid>",
  "title": "Fix billing sync", "description": "...",
  "status": "in_progress", "priority": "high",
  "assignee": { ...UserSerializer... },
  "reporter": { ...UserSerializer... },
  "due_date": "2026-09-20", "start_date": null,
  "estimated_hours": "4.00", "labels": ["bug","backend"],
  "created_by": { ... }, "updated_by": { ... },
  "created_at": "...", "updated_at": "..." }
```

> `labels` is a jsonb list and is **not filterable** — there is no FilterSet
> entry for it.

## `POST /tasks/`

**Request**
```json
{ "project": "<uuid>", "title": "Fix billing sync",
  "description": "...", "status": "todo", "priority": "high",
  "assignee_id": "<user uuid>", "due_date": "2026-09-20",
  "labels": ["bug"] }
```

Note `assignee_id` / `reporter_id` — **write-only UUIDs**. The response returns
the nested `assignee` / `reporter` objects instead:

```python
assignee    = UserSerializer(read_only=True)
assignee_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
```

**`workspace` is NOT accepted.** It is `read_only=True` and derived:

```python
def validate(self, attrs):
    project = attrs.get("project") or getattr(self.instance, "project", None)
    if project is None:
        raise ValidationError({"project": "This field is required."})
    attrs["workspace"] = project.workspace                 # ← derived
    if "assignee_id" in attrs:
        attrs["assignee"] = self._resolve_member(project.workspace, attrs.pop("assignee_id"), "assignee_id")
    if "reporter_id" in attrs:
        attrs["reporter"] = self._resolve_member(project.workspace, attrs.pop("reporter_id"), "reporter_id")
    return attrs
```

| Validation | Failure |
|---|---|
| `project` required | `400 {"project": ["This field is required."]}` |
| Assignee is a workspace member | `400 {"assignee_id": ["User is not a member of this workspace."]}` |
| Reporter is a workspace member | `400 {"reporter_id": [...]}` |
| Project must be visible to you | `400` from the `PrimaryKeyRelatedField` queryset, or the derived workspace fails `_require_membership` |

`create()` defaults `reporter` to the requesting user when not supplied.

**Response `201`.** Fires `task.created` in the audit log.

## `GET / PATCH / DELETE /tasks/{id}/`

PATCH re-runs the same `validate()`, so `workspace` is re-derived and member
checks re-run on any assignee change. `updated_by` is stamped.

**Tasks are also written by one other endpoint:**
`POST /handovers/{id}/review/` with `decision: approved` sets
`task.assignee = handover.to_user`. See [handovers.md](handovers.md).

---

## Hooks reference

| Hook | Call | Invalidates |
|---|---|---|
| `useProjects(params)` / `useProject(id)` | `GET /projects/` | — |
| `useCreateProject()` | `POST /projects/` | `["projects"]` |
| `useUpdateProject(id)` | `PATCH /projects/{id}/` | `["projects"]`, detail |
| `useDeleteProject()` | `DELETE` | `["projects"]` |
| `useTasks(params)` / `useTask(id)` | `GET /tasks/` | — |
| `useCreateTask()` | `POST /tasks/` | `["tasks"]` |
| `useUpdateTask(id)` | `PATCH /tasks/{id}/` | `["tasks"]`, `["tasks", id]` |
| `useDeleteTask()` | `DELETE` | `["tasks"]` |

All list hooks are gated: `enabled: !!params.workspace`, so nothing fires until a
workspace is selected.

---

## Common errors

| Symptom | Cause |
|---|---|
| `404` on a task you can see in another account | Not a member of its workspace |
| `400 {"project": [...]}` | Missing project, or a project in a workspace you cannot see |
| `400 {"assignee_id": [...]}` | Valid user UUID, but not a member of the project's workspace |
| `403 "You are not a member of this workspace."` | `_require_membership` on create — usually a stale `activeWorkspaceId` in localStorage |
| `500` on create right after someone else creates the same name | The slug check-then-act race — see [14](../14-algorithms.md#7-unique-slug-generation) |
