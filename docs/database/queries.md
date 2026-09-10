# Database — Important Queries

[← Schema overview](schema-overview.md) · [Relationships](relationships.md) ·
[Docs index](../README.md)

The queries that matter, as they appear in the code, with the SQL they generate
and what to watch out for.

**There is no raw SQL in this project** — verified. Everything below is ORM.

---

## 1. The tenancy query — the most important one

```python
self.queryset.filter(workspace__members__user=self.request.user).distinct()
```
`backend/apps/common/viewsets.py:31-32`

```sql
SELECT DISTINCT t.*
FROM tasks_task t
JOIN workspaces_workspace w ON t.workspace_id = w.id
JOIN workspaces_workspacemember m ON m.workspace_id = w.id
WHERE m.user_id = %s
ORDER BY t.created_at DESC;
```

**Runs on every list and every detail fetch** for projects, tasks, documents,
handovers, prompt templates. Variants of the same shape appear in comments,
activities and invitations.

| Property | Detail |
|---|---|
| Why `DISTINCT` | The membership join can duplicate rows |
| Why 404 not 403 | The row is not in the queryset, so `get_object()` raises `Http404` |
| Index used | `workspaces_workspacemember(workspace_id)` and the unique `(workspace, user)` |
| Improvement | Replace the join with `workspace_id__in=<subquery>` to drop the `DISTINCT` sort |

---

## 2. Vector similarity search

```python
DocumentChunk.objects
    .filter(workspace=workspace, embedding__isnull=False)
    .annotate(distance=CosineDistance("embedding", query_vector))
    .filter(distance__lte=0.75)
    .select_related("document")
    .order_by("distance")[:6]
```
`backend/apps/knowledge/services/search.py:51-59`

```sql
SELECT c.*, (c.embedding <=> %s) AS distance
FROM knowledge_documentchunk c
JOIN documents_document d ON c.document_id = d.id
WHERE c.workspace_id = %s
  AND c.embedding IS NOT NULL
  AND (c.embedding <=> %s) <= 0.75
ORDER BY distance
LIMIT 6;
```

| | |
|---|---|
| Operator | `<=>` — pgvector cosine distance |
| Index | HNSW, `vector_cosine_ops` — must match the operator or the index is unusable |
| Complexity | ~O(log n) with HNSW, versus O(n) full scan |
| Tenant safety | `workspace_id` filter comes **first**; retrieval cannot cross tenants |
| Score | `round(max(0, 1 - distance), 4)` in Python |

**Watch out:** the `distance <= 0.75` filter is applied to a computed expression,
so PostgreSQL evaluates it after the index scan produces candidates. Raising
`SEARCH_TOP_K` a lot would change the cost profile.

---

## 3. Dashboard — 10 counts + 4 lists

```python
projects  = Project.objects.filter(workspace=workspace)
tasks     = Task.objects.filter(workspace=workspace)
documents = Document.objects.filter(workspace=workspace)
handovers = Handover.objects.filter(workspace=workspace)
today     = timezone.now().date()

stats = {
  "total_projects":    projects.count(),
  "active_projects":   projects.filter(status=ACTIVE, archived=False).count(),
  "archived_projects": projects.filter(archived=True).count(),
  "total_tasks":       tasks.count(),
  "pending_tasks":     tasks.filter(status__in=OPEN_TASK_STATUSES).count(),
  "completed_tasks":   tasks.filter(status=COMPLETED).count(),
  "overdue_tasks":     tasks.filter(due_date__lt=today, status__in=OPEN_TASK_STATUSES).count(),
  "total_documents":   documents.count(),
  "my_tasks":          tasks.filter(assignee=request.user, status__in=OPEN_TASK_STATUSES).count(),
  "pending_handovers": handovers.filter(status=PENDING).count(),
}
```
`backend/apps/core/views.py:104-125`

**Ten separate `SELECT COUNT(*)`**, plus four `[:5]` list queries, plus two more
per document row from `DocumentSerializer`. Roughly 15+ queries on the first page
every user loads.

### The fix

```python
tasks.aggregate(
    total     = Count("id"),
    pending   = Count("id", filter=Q(status__in=OPEN_TASK_STATUSES)),
    completed = Count("id", filter=Q(status=COMPLETED)),
    overdue   = Count("id", filter=Q(due_date__lt=today, status__in=OPEN_TASK_STATUSES)),
    mine      = Count("id", filter=Q(assignee=request.user, status__in=OPEN_TASK_STATUSES)),
)
```

One query with `FILTER (WHERE ...)` clauses instead of five. Same for projects.
15+ becomes about 7.

Index used: `tasks_task(workspace, status)`.

---

## 4. Analytics aggregates

### Status and priority breakdowns

```python
tasks.values("status").annotate(count=Count("id"))
```

```sql
SELECT status, COUNT(id) FROM tasks_task WHERE workspace_id = %s GROUP BY status;
```

Clean, indexed by `(workspace, status)`.

### The weekly series

```python
tasks.filter(created_at__date__gte=window_start).values_list("created_at", flat=True)
```

**This pulls every matching timestamp into Python** and buckets them there. Fine
for an 8-week window; at scale, `TruncWeek` + `GROUP BY` would push it into SQL —
though you would still have to fill empty weeks in Python.

### Average review time

```python
reviewed.annotate(wait=F("reviewed_at") - F("created_at")).aggregate(avg=Avg("wait"))
```

```sql
SELECT AVG(reviewed_at - created_at)
FROM handovers_handover
WHERE workspace_id = %s AND reviewed_at IS NOT NULL;
```

The subtraction and the average both happen **in PostgreSQL**, using its native
`interval` type. Only the `/3600` rounding is done in Django. Returns `NULL` when
nothing has been reviewed.

### Workload

```python
tasks.filter(assignee__isnull=False, status__in=OPEN_TASK_STATUSES)
     .values("assignee_id", "assignee__name", "assignee__email")
     .annotate(count=Count("id")).order_by("-count")[:8]
```

One `GROUP BY` with a join to `accounts_user`, ordered and limited in SQL.

---

## 5. The N+1 queries — all of them

### The worst: document list

```python
def get_embedding_status(self, obj):
    job = obj.embedding_jobs.order_by("-created_at").first()    # 1 query PER ROW
    return job.status if job else None

def get_chunk_count(self, obj):
    return obj.chunks.count()                                    # 1 query PER ROW
```
`backend/apps/documents/serializers.py:60-66`

20 documents = 41 queries.

**Fix:**

```python
queryset = (Document.objects
    .select_related("workspace","project","uploaded_by","created_by","updated_by")
    .annotate(chunk_total=Count("chunks", distinct=True))
    .prefetch_related(Prefetch("embedding_jobs",
        queryset=EmbeddingJob.objects.order_by("-created_at"), to_attr="recent_jobs")))
```
then read `obj.chunk_total` and `obj.recent_jobs[0] if obj.recent_jobs else None`.
41 queries → 3.

### The cheaper ones

| Field | File | Fix |
|---|---|---|
| `member_count = IntegerField(source="members.count")` | `workspaces/serializers.py:28` | `.annotate(member_count=Count("members"))` |
| `task_count = IntegerField(source="tasks.count")` | `projects/serializers.py:11` | `.annotate(task_count=Count("tasks"))` |
| `reply_count = IntegerField(source="replies.count")` | `comments/serializers.py:19` | `.annotate(reply_count=Count("replies"))` |

Each is one extra query per row.

---

## 6. `select_related` — where it is already right

Every scoped viewset prefetches what its serializer nests:

```python
# tasks
select_related("workspace","project","assignee","reporter","created_by","updated_by")
# handovers
select_related("workspace","task","task__project","from_user","to_user","reviewer","created_by","updated_by")
# projects
select_related("workspace","owner","created_by","updated_by")
# documents
select_related("workspace","project","uploaded_by","created_by","updated_by")
# comments
select_related("author","content_type")
# activities
select_related("actor","content_type")
# notifications
select_related("actor")
# workspaces
select_related("owner").prefetch_related("members")
```

`task__project` on handovers is the subtle one — the serializer exposes
`project_id` from the task, so without it every row would issue an extra query.

Without these, a 20-row task page would fire roughly 100 extra queries, because
`TaskSerializer` nests four `UserSerializer`s.

---

## 7. Filtered queries by endpoint

| Endpoint | Generated shape |
|---|---|
| `/tasks/?status=todo&priority=high` | `WHERE workspace_id IN (...) AND status='todo' AND priority='high'` |
| `/tasks/?due_before=2026-10-01` | `AND due_date <= '2026-10-01'` |
| `/handovers/?project=<uuid>` | joins `tasks_task` — `AND t.project_id = %s` |
| `/documents/?file_type__icontains=pdf` | `AND file_type ILIKE '%pdf%'` — **not indexable** |
| `/activities/?date_from=&date_to=` | `AND created_at::date >= %s AND created_at::date <= %s` — the `::date` cast prevents index use on `created_at` |
| `/comments/?target_type=task&target_id=` | `AND content_type_id = %s AND object_id = %s` — uses `(content_type, object_id)` |
| `?search=foo` on any list | `ILIKE '%foo%'` OR-ed across `search_fields` — **full scan** |

**DRF's `SearchFilter` always produces leading-wildcard `ILIKE`.** That is fine at
current data sizes but is the first thing to convert to PostgreSQL full-text
search if search ever feels slow.

---

## 8. The RAG structured-context query

```python
q = Q()
for t in terms:                       # up to 8 keywords
    q |= Q(title__icontains=t) | Q(project__name__icontains=t)
task_qs = task_qs.filter(q).order_by("due_date")[:10]
```
`backend/apps/ai/services/rag.py:67-74`

```sql
WHERE workspace_id = %s
  AND ( title ILIKE '%term1%' OR p.name ILIKE '%term1%'
     OR title ILIKE '%term2%' OR p.name ILIKE '%term2%' ... )
ORDER BY due_date LIMIT 10;
```

Up to 16 leading-wildcard `ILIKE` predicates, none indexable. Only runs on AI
chat, which is rate-limited to 30/hour per user and dominated by the LLM round
trip — so low practical impact.

Improvement: a `pg_trgm` GIN index makes `ILIKE` indexable, or reuse the vector
search over task titles.

---

## 9. Bulk operations

### Chunk storage

```python
@transaction.atomic
def _store_chunks(document, chunks, vectors):
    DocumentChunk.objects.filter(document=document).delete()
    rows = [DocumentChunk(...) for chunk, vector in zip(chunks, vectors)]
    DocumentChunk.objects.bulk_create(rows, batch_size=200)
```

One DELETE plus a handful of multi-row INSERTs, all atomic. A 200-chunk document
is not 200 round trips.

**Note:** `bulk_create` does **not** fire `post_save`, so chunks produce no audit
rows — correct, they are derived data.

### Mark all notifications read

```python
Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
```

One UPDATE. **No signals.** Intentional here.

### Blacklist every refresh token

```python
for outstanding in OutstandingToken.objects.filter(user=user):
    BlacklistedToken.objects.get_or_create(token=outstanding)
```

A loop with one `get_or_create` per token. For a long-lived active user that
could be hundreds of round trips inside a password-reset request. A
`bulk_create(..., ignore_conflicts=True)` would be one query.

---

## 10. Queries by table — who reads what

| Table | Hottest read | Where |
|---|---|---|
| `workspaces_workspacemember` | membership lookup | **every** permission check, every scoped query |
| `tasks_task` | scoped list, dashboard counts | tasks page, dashboard, analytics, RAG |
| `knowledge_documentchunk` | vector kNN | AI search, chat, summarise, generate-tasks |
| `notifications_notification` | `COUNT WHERE recipient AND NOT is_read` | the bell, every 30s when the socket is down |
| `activities_activity` | filtered list + CSV | audit page, detail-page timelines |
| `comments_comment` | `WHERE content_type AND object_id` | every task/project/document detail page |
| `accounts_user` | PK lookup by JWT | **every authenticated request** |

`accounts_user` is read on literally every request — `JWTAuthentication` resolves
`request.user` from the token's `user_id`. That is a single indexed PK lookup, but
it is also the argument for connection pooling: it is one more round trip on a
connection that was just opened.

---

## 11. How to inspect queries in this project

`django-debug-toolbar` is **not** installed. Options:

```python
# See the SQL for a queryset
print(Task.objects.filter(workspace=ws).query)

# Count queries for a block
from django.test.utils import CaptureQueriesContext
from django.db import connection
with CaptureQueriesContext(connection) as ctx:
    ...
print(len(ctx.captured_queries))

# In a test
self.assertNumQueries(5):
    self.client.get("/api/v1/tasks/?workspace=...")

# After a request in shell/dev (DEBUG=True only)
from django.db import connection
connection.queries
```

`assertNumQueries` is the right tool for locking in an N+1 fix so it cannot
regress — and none of the current tests use it.
