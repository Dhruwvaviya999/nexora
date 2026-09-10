# API — Handovers

[← API index](README.md) · [Module deep dive](../modules/handovers.md)

Base: `/api/v1/handovers/` · ViewSet: `HandoverViewSet(WorkspaceScopedViewSet)`
· `backend/apps/handovers/views.py`

---

## `GET /handovers/`

**Auth:** member (scoped by `get_queryset()`)

**Filters** — `HandoverFilter`:

| Param | Maps to |
|---|---|
| `workspace` | exact |
| `task` | exact |
| `project` | `task__project_id` — **custom**, the model has no such field |
| `status` | `pending` / `approved` / `rejected` |
| `from_user`, `to_user` | exact |
| `search` | `summary`, `pending_items`, `task__title` |
| `ordering` | `created_at`, `updated_at`, `status`, `reviewed_at` |
| `page` | pagination |

**Response `200`** — paginated envelope of `HandoverSerializer`:

```json
{
  "id": "<uuid>",
  "workspace": "<uuid>",
  "task": "<uuid>",
  "task_title": "Fix billing sync",
  "project_id": "<uuid>",
  "from_user": { "id": "...", "name": "...", "email": "...", "avatar": "" },
  "to_user":   { ... },
  "summary": "...",
  "pending_items": "...",
  "resources": "...",
  "status": "pending",
  "reviewer": null,
  "review_comment": "",
  "reviewed_at": null,
  "created_by": { ... }, "updated_by": { ... },
  "created_at": "...", "updated_at": "..."
}
```

`task_title` and `project_id` are convenience read fields so lists need no extra
requests. `select_related("task__project")` on the queryset is what keeps that
free.

The reviewer queue is just this endpoint with `?status=pending`
(`/handovers/reviews` page).

---

## `POST /handovers/`

**Auth:** member

**Request**
```json
{ "task": "<uuid>", "to_user_id": "<uuid>",
  "summary": "Migrated the webhook handler...",
  "pending_items": "Retry logic still TODO",
  "resources": "Runbook: https://..." }
```

**Validation** — `HandoverSerializer.validate`:

| Check | Failure |
|---|---|
| `task` required | `400 {"task": ["This field is required."]}` |
| `workspace = task.workspace` | derived, read-only |
| `to_user` must be a workspace member | `400 {"to_user_id": ["User is not a member of this workspace."]}` |
| `to_user != request.user` | `400 {"to_user_id": ["You can't hand a task over to yourself."]}` |
| `summary` non-blank | model-level |

`create()` sets `from_user = request.user`. `perform_create()` (inherited) checks
membership and stamps `created_by`/`updated_by`.

**Response `201`** — the full serializer.

**Side effects**
1. `activities_activity` row `handover.created` (signal)
2. `create_notification(HANDOVER_SUBMITTED)` → the recipient, link
   `/handovers/{id}`
3. WebSocket push to the recipient, after commit

---

## `GET /handovers/{id}/`

**Auth:** member. A non-member gets **404**, not 403 — the queryset filter.

---

## `PATCH /handovers/{id}/`

**Auth: the submitter only, and only while `pending`.**

```python
def perform_update(self, serializer):
    handover = self.get_object()
    if handover.from_user_id != self.request.user.pk:
        raise PermissionDenied("Only the submitter can edit a handover.")
    super().perform_update(serializer)
```

Plus, in the serializer:

| Check | Failure |
|---|---|
| Status is `pending` | `400 "Only pending handovers can be edited."` |
| `task` unchanged | `400 {"task": ["The task of a handover can't be changed."]}` |

Editable: `summary`, `pending_items`, `resources`, `to_user_id`.

---

## `DELETE /handovers/{id}/`

**Auth:** the submitter, **or** a member with a reviewer role.

```python
def perform_destroy(self, instance):
    if instance.status != HandoverStatus.PENDING:
        raise ValidationError("Only pending handovers can be deleted.")
    is_submitter = instance.from_user_id == self.request.user.pk
    if not is_submitter and self._reviewer_membership(instance.workspace) is None:
        raise PermissionDenied("Only the submitter or a workspace manager can delete a handover.")
    instance.delete()
```

**Response `204`.** Hard delete — there is no soft-delete flag on handovers.
Fires `handover.deleted` in the audit log.

---

## `POST /handovers/{id}/review/` ⭐

The most consequential endpoint in the product.

| | |
|---|---|
| **Auth** | **owner / admin / manager only** (`REVIEWER_ROLES`) |
| **Precondition** | status must be `pending` |
| **Serializer** | `HandoverReviewSerializer` |

**Request**
```json
{ "decision": "approved" }
```
or
```json
{ "decision": "rejected", "comment": "Please add the API credentials." }
```

**Validation**

| Check | Failure |
|---|---|
| Caller has a reviewer role | `403 "Only workspace owners, admins, and managers can review handovers."` |
| Not already reviewed | `400 "This handover has already been reviewed."` |
| `decision` ∈ {`approved`, `rejected`} | `400` — `pending` is not a valid decision |
| **Rejection requires a comment** | `400 {"comment": ["A comment is required when rejecting a handover."]}` |
| `comment` ≤ 5000 chars | `400` |

**What the handler writes**

```python
handover.status = decision
handover.reviewer = request.user
handover.review_comment = comment
handover.reviewed_at = timezone.now()
handover.updated_by = request.user
handover.save(update_fields=["status","reviewer","review_comment",
                             "reviewed_at","updated_by","updated_at"])

if approved and handover.to_user is not None:
    task = handover.task
    task.assignee = handover.to_user
    task.updated_by = request.user
    task.save(update_fields=["assignee","updated_by","updated_at"])
    create_notification(TASK_ASSIGNED → to_user, link=f"/tasks/{task.pk}")

create_notification(HANDOVER_REVIEWED → from_user, link=f"/handovers/{pk}")
```

**Response `200`** — the updated `HandoverSerializer`.

### Effects table

| | Approved | Rejected |
|---|---|---|
| `handovers_handover` | status, reviewer, comment, reviewed_at | same |
| **`tasks_task`** | **`assignee = to_user`** | untouched |
| Notifications | 2 (recipient + submitter) | 1 (submitter) |
| Audit rows | 2 (`handover.updated`, `task.updated`) | 1 |
| Frontend invalidation | `["handovers"]`, `["handovers", id]`, `["tasks"]` | same |

### Two things to notice

1. **`to_user is not None` guard** — the FK is `SET_NULL`, so a deleted
   recipient does not crash the review.
2. **No transaction wraps the two saves.** A crash between them would leave the
   handover approved but the task unassigned. `@transaction.atomic` would fix it.
   Flagged in [25-known-limitations.md](../25-known-limitations.md).

---

## `GET /handovers/{id}/export/`

| | |
|---|---|
| **Auth** | member |
| **Response** | `200 application/pdf` |
| **Header** | `Content-Disposition: attachment; filename="handover-<slug>.pdf"` |

```python
from apps.handovers.pdf import render_handover_pdf     # local import
handover = self.get_object()
pdf = render_handover_pdf(handover)
filename = f"handover-{slugify(handover.task.title) or handover.pk}.pdf"
```

The local import means the app still works if reportlab is not installed
(comment at `views.py:153-154`).

**Client side:** this endpoint cannot go through `apiClient`, which parses JSON.
`frontend/src/lib/api/download.ts` fetches with the bearer token, reads the blob,
recovers the filename from `Content-Disposition`, and triggers a download.

```ts
await downloadFile(API_ROUTES.handovers.export(handover.id), "handover.pdf");
```
`app/(app)/handovers/[id]/page.tsx:108-111`

> `downloadFile` has **no refresh-retry**. An expired token at download time
> fails with a toast rather than refreshing.

---

## Hooks reference

| Hook | Call | Invalidates |
|---|---|---|
| `useHandovers(params)` | `GET /handovers/` | — |
| `useHandover(id)` | `GET /handovers/{id}/` | — |
| `useCreateHandover()` | `POST /handovers/` | `["handovers"]` |
| `useUpdateHandover(id)` | `PATCH /handovers/{id}/` | `["handovers"]`, `["handovers", id]` |
| `useDeleteHandover()` | `DELETE /handovers/{id}/` | `["handovers"]` |
| `useReviewHandover(id)` | `POST /handovers/{id}/review/` | `["handovers"]`, `["handovers", id]`, **`["tasks"]`** |

`frontend/src/hooks/use-handovers.ts`
