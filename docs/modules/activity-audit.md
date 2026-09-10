# Module — Activity & Audit Trail

[← Modules index](../12-business-modules.md) · [← Docs index](../README.md)

The smallest module in the project and the most elegant. Worth studying out of
proportion to its size.

---

## 1. The problem it solves

"Who changed this, and when?" An append-only trail of every meaningful write in a
workspace, filterable and exportable to CSV.

---

## 2. Who uses it

Any workspace **member** can read the log for workspaces they belong to. There is
no role restriction on reading it, and no way to write to it through the API —
it is read-only by design (`ReadOnlyModelViewSet`).

---

## 3. Frontend

| Route | File |
|---|---|
| `/activity` | `app/(app)/activity/page.tsx` |

Hooks: `useActivities` (filters) and `useWorkspaceMembers` (the actor dropdown).
CSV export goes through `lib/api/download.ts`, not `apiClient`.

Per-object timelines appear inside
`components/comments/collaboration-tabs.tsx` on task, project and document detail
pages, using `?target_type=` and `?target_id=`.

`lib/activity.ts` maps the dotted action strings (`task.created`,
`project.archived`) to human labels and icons — the frontend half of the format
contract.

---

## 4. Backend

```
apps/activities/
├── models.py       Activity
├── handlers.py     ALL the signal wiring
├── services.py     log_activity() + the delete-suppression guard
├── serializers.py  ActivitySerializer
├── views.py        ActivityViewSet + export action
├── apps.py         ready() → imports handlers
└── tests.py        3 tests
```

**No domain app imports `activities`.** Audit logging is attached entirely from
the outside. That is the cleanest decoupling in the codebase.

---

## 5. Database

**One table: `activities_activity`.**

| Column | Purpose |
|---|---|
| `actor_id` | Who (nullable, `SET_NULL`) |
| `workspace_id` | Which tenant (`CASCADE`) |
| `action` | A dotted string: `task.created`, `project.archived`, `member.invited` |
| `content_type_id` + `object_id` | Generic pointer to the affected object — **null for deletes** |
| `metadata` | jsonb: a small human-readable snapshot |

Indexes: `(workspace, created_at)` for the main view, `(content_type, object_id)`
for per-object timelines.

### Why `metadata` is a snapshot, not a join

```python
_register_audited(Task, "task", lambda i: {"title": i.title, "status": i.status})
```

The metadata records what was true **at the time of the event**. So the log still
reads correctly after the task is renamed — and, crucially, after it is
**deleted**, when `content_type`/`object_id` are null and there is nothing left to
join to.

---

## 6. The signal wiring

`backend/apps/activities/handlers.py` — the whole module is 90 lines.

```python
def _register_audited(model, entity, label):
    def on_save(sender, instance, created, **kwargs):
        log_activity(actor=_audit_actor(instance, created),
                     workspace=instance.workspace,
                     action=f"{entity}.{'created' if created else 'updated'}",
                     target=instance, metadata=label(instance))

    def on_delete(sender, instance, **kwargs):
        log_activity(actor=instance.updated_by or instance.created_by,
                     workspace=instance.workspace,
                     action=f"{entity}.deleted", metadata=label(instance))

    post_save.connect(on_save,   sender=model, weak=False, dispatch_uid=f"activity_save_{entity}")
    post_delete.connect(on_delete, sender=model, weak=False, dispatch_uid=f"activity_delete_{entity}")

_register_audited(Project,  "project",  lambda i: {"name": i.name, "archived": i.archived})
_register_audited(Task,     "task",     lambda i: {"title": i.title, "status": i.status})
_register_audited(Document, "document", lambda i: {"title": i.title})
_register_audited(Handover, "handover", lambda i: {"task": i.task.title, "status": i.status})
```

**Adding audit logging to a new model is one line.** That is the payoff, and the
module docstring says so: *"Domain apps stay untouched — adding history is just
registering a model here."*

Two Django details that matter:

- **`weak=False`** — the handler closures are not referenced anywhere else and
  would otherwise be garbage-collected. The docstring calls this out.
- **`dispatch_uid`** — prevents double registration if the module is imported
  twice, which would double every audit row.

Comments, workspaces and memberships get their own handlers because their actor
and metadata rules differ. Comments additionally skip soft-deleted rows:

```python
if not created or instance.is_deleted: return
```

### The one direct call

`apps/invitations/views.py:123` calls `log_activity` directly for
`member.invited`, because no model save corresponds to "an invitation was sent"
in the way the signal factory expects.

---

## 7. The cascade-delete guard

The single most interesting piece of code in this module.

```python
_workspaces_being_deleted: set[str] = set()

def suppress_activity_for_workspace(pk): _workspaces_being_deleted.add(str(pk))
def resume_activity_for_workspace(pk):   _workspaces_being_deleted.discard(str(pk))

def log_activity(*, actor, workspace, action, target=None, metadata=None):
    workspace_pk = getattr(workspace, "pk", workspace)
    if workspace_pk is not None and str(workspace_pk) in _workspaces_being_deleted:
        return None
    ...
```
`backend/apps/activities/services.py:15-32`

The comment explains the bug it fixes:

> Deleting a workspace cascades into every child object, and each cascade fires
> the `post_delete` handlers. Those would append activity rows referencing a
> workspace that is about to be removed, which the database rejects as a foreign
> key violation when the transaction commits — taking the whole delete down with
> it. The rows would be pointless anyway: `Activity.workspace` cascades, so they
> die with the workspace.

`pre_delete` on `Workspace` calls `suppress_...`, `post_delete` calls
`resume_...`.

**This is real, hard-won debugging** and excellent interview material: a
`post_delete` handler that writes a row referencing the object being deleted is a
subtle, cascade-only failure that would not show up in any single-object test.

**Its weakness, honestly stated:** `_workspaces_being_deleted` is a
process-local, mutable module global. It works because the delete and its cascade
happen inside one request in one process. It would not protect a delete split
across processes, and it is not thread-safe in a way that would matter under an
unusual concurrency model.

---

## 8. API

| Method | Endpoint | Notes |
|---|---|---|
| GET | `/activities/` | Filters below |
| GET | `/activities/{id}/` | |
| GET | `/activities/export/` | CSV, capped at 10,000 rows |

**Filters** (hand-rolled in `get_queryset`, not django-filter):
`?workspace=` `?action=task.created` `?actor=<uuid>` `?date_from=YYYY-MM-DD`
`?date_to=YYYY-MM-DD` `?target_type=task` `?target_id=<uuid>`

Scoping is the same pattern as everywhere:
`filter(workspace__members__user=self.request.user).distinct()`

### CSV export

```python
response = HttpResponse(content_type="text/csv")
response["Content-Disposition"] = 'attachment; filename="audit-log.csv"'
writer = csv.writer(response)
writer.writerow(["timestamp","actor","action","target_type","target_id","metadata"])
for activity in self.get_queryset()[:EXPORT_LIMIT]:      # 10_000
    writer.writerow([...])
```

Two properties: it reuses `get_queryset()`, so **the export respects the current
filters**; and `EXPORT_LIMIT` bounds the response — the comment says exactly that.

The improvement (`StreamingHttpResponse` + `.iterator()`) is in
[19-performance-scalability.md](../19-performance-scalability.md).

---

## 9. What gets logged

| Action | Fired by |
|---|---|
| `project.created` / `.updated` / `.deleted` | signal |
| `task.created` / `.updated` / `.deleted` | signal |
| `document.created` / `.updated` / `.deleted` | signal |
| `handover.created` / `.updated` / `.deleted` | signal |
| `comment.created` | signal (skips soft-deleted) |
| `workspace.created` / `.updated` | signal |
| `member.*` (added / removed) | signal on `WorkspaceMember` |
| `member.invited` | **direct call** in `invitations/views.py:123` |

Note `project.archived` appears in `lib/activity.ts` on the frontend as a
distinct label, but the backend emits `project.updated` with
`metadata.archived = true` — the archive action goes through `save()`, not a
dedicated action string. *Not confirmed whether the frontend derives the archived
label from the metadata; that would need reading `lib/activity.ts` in full.*

---

## 10. The blind spot

**Signals only fire on ORM `save()`/`delete()` of a model instance.** These
bypass them entirely:

| Operation | Logged? |
|---|---|
| `Model.objects.create()` / `instance.save()` | ✅ |
| `instance.delete()` | ✅ |
| `queryset.update(...)` | ❌ |
| `queryset.delete()` | ⚠️ fires `post_delete` per object in most cases, but not for fast-delete paths |
| `bulk_create()` | ❌ |
| Raw SQL / psql | ❌ |
| A data migration | ❌ unless it goes through the ORM per-instance |

A live example: `NotificationViewSet.read_all` uses
`.update(is_read=True)` — deliberately, for one query — and produces no audit
row. Notifications are not audited, so it does not matter there. But it is the
pattern to watch when adding new code.

---

## 11. Failure scenarios

| Scenario | Result |
|---|---|
| Delete a workspace | Suppression guard prevents FK violations; the log dies with the workspace |
| Delete the actor's user account | `actor` becomes NULL; the row survives with "" in the CSV |
| Export more than 10,000 rows | Truncated silently at the cap |
| A `label()` lambda raises (e.g. `i.task.title` on a handover whose task is gone) | The signal handler raises **inside the save transaction** — this would fail the write. *Not confirmed whether any path can produce that; `Handover.task` is `CASCADE`, so the handover is deleted first* |
| Write via `queryset.update()` | Silently unaudited |

---

## 12. Dependencies

**Depends on:** `apps.comments`, `apps.documents`, `apps.handovers`,
`apps.projects`, `apps.tasks`, `apps.workspaces` — it imports **six** domain apps
in `handlers.py` in order to register receivers.

**Depended on by:** `apps.invitations` (one direct `log_activity` call) and
`apps.ai.services.summarizer` (activity summaries).

The import direction is inverted from every other module: `activities` reaches
*into* the domain apps, so the domain apps never have to know about it.

---

## 13. Interview questions

1. How does the audit log work? Where is it written?
2. Why signals instead of calling `log_activity` in each view?
   *(One line per model; domain apps stay clean. Cost: implicit behaviour, and a
   blind spot for non-ORM writes.)*
3. Why `weak=False` on the signal connections?
4. What is `dispatch_uid` for?
5. Why is `metadata` a snapshot instead of a join to the live object?
6. Explain the workspace-deletion guard. What bug does it fix?
   *(Best question in this module.)*
7. What is wrong with `_workspaces_being_deleted` as an approach?
8. Which writes does the audit log miss?
9. Why is `content_type` null on delete rows?
10. How would you make the CSV export handle a million rows?
11. `Activity` is append-only by convention, not enforcement. How would you
    enforce it? *(Revoke UPDATE/DELETE at the database role level; the ORM cannot
    guarantee it.)*
