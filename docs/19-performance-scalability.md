# 19 — Performance & Scalability

[← Back to index](README.md)

Only issues traceable to real code. Nothing speculative.

Format for each: **current implementation → possible problem → impact →
improvement**.

---

## 1. Where the codebase already gets it right

Worth knowing, because an interviewer will ask what you did well.

### 1.1 `select_related` on every scoped viewset

```python
queryset = Task.objects.select_related(
    "workspace", "project", "assignee", "reporter", "created_by", "updated_by")
```
`backend/apps/tasks/views.py:11-13`

`TaskSerializer` nests four `UserSerializer`s plus the project. Without
`select_related`, a 20-row page would issue ~100 extra queries. Every scoped
viewset does this — projects, tasks, documents, handovers, comments, activities,
notifications, mentions, invitations, AI conversations.

### 1.2 Indexes that match real queries

Fourteen explicit `Meta.indexes` entries, each mapping to a query that actually
exists. See [09-database-architecture.md](09-database-architecture.md#7-indexes).
`(recipient, is_read)` exists precisely because the unread badge polls.

### 1.3 The embedding pipeline is asynchronous

An upload returns as soon as the file is stored. Embedding — model load, text
extraction, N vector computations — happens on a worker.

### 1.4 The model is cached in-process

`_MODELS` in `sentence_transformer.py:16` and `_INSTANCES` in
`embeddings/factory.py:22`. The first embed pays the ~90 MB load; every call
after reuses it.

### 1.5 Websockets replace polling

`refetchInterval: isLive ? false : 30_000` (`hooks/use-notifications.ts:37`).
A live client makes **zero** periodic requests. With 500 concurrent users that is
1000 requests/minute saved.

### 1.6 Single-flight token refresh

Ten simultaneous 401s produce one refresh call, not ten.

### 1.7 Bulk insert for chunks

`DocumentChunk.objects.bulk_create(rows, batch_size=200)` — a 200-chunk document
is a handful of INSERTs, not 200.

### 1.8 Query-key-based cache reuse

Because params are part of the key, going back to a previously viewed page or
filter is instant.

---

## 2. Real issues, ranked

### 🔴 2.1 N+1 on the document list

**Current:**

```python
def get_embedding_status(self, obj):
    job = obj.embedding_jobs.order_by("-created_at").first()   # 1 query per row
    return job.status if job else None

def get_chunk_count(self, obj):
    return obj.chunks.count()                                   # 1 query per row
```
`backend/apps/documents/serializers.py:60-66`

**Problem:** two extra queries per document. A 20-row page = 1 + 40 queries. The
`select_related` on the viewset does not help, because these are reverse
relations accessed inside `SerializerMethodField`s.

**Impact:** the `/documents` page and the `/ai` hub are the slowest reads in the
app. It also affects `/projects/[id]`, which lists documents.

**Improvement:**

```python
queryset = Document.objects.select_related(...).annotate(
    chunk_total=Count("chunks", distinct=True)
).prefetch_related(
    Prefetch("embedding_jobs",
             queryset=EmbeddingJob.objects.order_by("-created_at"),
             to_attr="recent_jobs")
)
```
then read `obj.chunk_total` and `obj.recent_jobs[0]`. Turns 41 queries into 3.

### 🟠 2.2 Count-heavy `SerializerMethodField`s elsewhere

| Field | File | Cost |
|---|---|---|
| `member_count` | `workspaces/serializers.py:28` — `source="members.count"` | 1 query per workspace |
| `task_count` | `projects/serializers.py:11` — `source="tasks.count"` | 1 query per project |
| `reply_count` | `comments/serializers.py:19` — `source="replies.count"` | 1 query per comment |

**Impact:** a 20-project list is 21 queries; a 50-comment thread is 51.

**Improvement:** `.annotate(task_count=Count("tasks"))` on the viewset queryset
and drop the `source=`. Same output, one query.

### 🟠 2.3 The dashboard fires 15+ queries

`backend/apps/core/views.py:104-152` — ten separate `.count()` calls plus four
`[:5]` list queries, all against the same workspace.

**Impact:** measurable latency on the first screen every user sees. It is also
the endpoint hit most often.

**Improvement:** collapse the task counts into one aggregate:

```python
tasks.aggregate(
    total=Count("id"),
    pending=Count("id", filter=Q(status__in=OPEN)),
    completed=Count("id", filter=Q(status=COMPLETED)),
    overdue=Count("id", filter=Q(due_date__lt=today, status__in=OPEN)),
    mine=Count("id", filter=Q(assignee=request.user, status__in=OPEN)),
)
```
Five queries become one. Same for projects. That takes 15+ down to about 7.

Second option: cache the whole payload in Redis for 30–60 seconds keyed by
`(workspace, user)`. The dashboard is not a real-time view.

### 🟠 2.4 No database connection pooling

**Current:** `CONN_MAX_AGE` is not set anywhere — verified. Django's default is
`0`, so **every request opens and closes a PostgreSQL connection.**

**Impact:** a TCP handshake plus PostgreSQL backend fork per request — typically
1–5 ms wasted, more under load. PostgreSQL's default `max_connections` (100)
becomes the hard ceiling: 3 uvicorn workers × concurrency plus 2 Celery workers
can approach it.

**Improvement:** set `CONN_MAX_AGE = 60` (persistent connections), or put
PgBouncer in front in transaction-pooling mode. PgBouncer is the right answer if
you ever run more than a handful of processes.

### 🟡 2.5 Analytics computes everything live

`AnalyticsView` (`core/views.py:163-260`) runs on every page load: two
`GROUP BY`s, two full scans of an 8-week window, a workload aggregate and a
handover aggregate.

**Impact:** fine at demo scale. At 100k tasks per workspace the 8-week window
scans get expensive, and `values_list("created_at", flat=True)` pulls every
matching timestamp into Python.

**Improvement:** cache for 5–15 minutes (analytics is not real-time), or move the
bucketing into SQL with `TruncWeek` + `Count`, or maintain a daily rollup table.

### 🟡 2.6 `ILIKE '%term%'` in the RAG structured context

```python
q |= Q(title__icontains=t) | Q(project__name__icontains=t)
```
`backend/apps/ai/services/rag.py:70-73`

**Problem:** a leading-wildcard `ILIKE` cannot use a B-tree index. Up to 8 terms
OR-ed together means up to 8 full scans of the workspace's tasks per chat message.

**Impact:** only on AI chat, which is already rate-limited to 30/hour per user
and dominated by the LLM round trip. Low practical impact today.

**Improvement:** a `pg_trgm` GIN index makes `ILIKE` indexable; or use
PostgreSQL full-text search; or reuse the existing vector search over task titles.

### 🟡 2.7 The CSV export builds the whole response in memory

```python
response = HttpResponse(content_type="text/csv")
writer = csv.writer(response)
for activity in self.get_queryset()[:EXPORT_LIMIT]:    # 10,000
    writer.writerow([...])
```
`backend/apps/activities/views.py:73-94`

**Problem:** 10,000 rows are serialised into one in-memory response. Also, the
queryset `select_related("actor", "content_type")` helps, but `activity.metadata`
is a dict written straight into the CSV cell via `str()`.

**Impact:** a few MB of memory per export and a slow response. The 10,000 cap is
the mitigation and it is deliberate.

**Improvement:** `StreamingHttpResponse` with a generator, plus
`.iterator(chunk_size=2000)` on the queryset.

### 🟡 2.8 `.distinct()` on every scoped queryset

`filter(workspace__members__user=...)` joins through the membership table and can
duplicate rows, so `.distinct()` is required. But `DISTINCT` forces a sort or
hash over the full result set.

**Improvement:** replace the join with a subquery, which needs no `DISTINCT`:

```python
Task.objects.filter(workspace__in=Workspace.objects.filter(members__user=user))
```
or `filter(workspace__members__user=user)` → `filter(workspace_id__in=<member workspace ids>)`
with the id list computed once per request.

### 🟡 2.9 Three sequential round trips before the dashboard renders

`/auth/me/` → `/workspaces/` → `/dashboard/?workspace=`. Each waits for the last,
because the workspace id is not known until step 2 returns.

**Impact:** roughly 3× the latency to first meaningful paint.

**Improvement:** persist the last workspace id in the token or a cookie and start
the dashboard fetch in parallel with `/auth/me/`; or add a single
`/auth/bootstrap/` endpoint returning user + workspaces + dashboard.

### 🟢 2.10 Missing indexes

`projects_project` is filtered by `(workspace, status, archived)` and
`documents_document` by `(workspace, project)`, but neither has a composite
index. The FK index on `workspace_id` carries most of the load, so impact is low
until row counts grow.

### 🟢 2.11 Unbounded tables

| Table | Grows with | Pruned? |
|---|---|---|
| `token_blacklist_outstandingtoken` | every token refresh | ❌ no beat schedule exists |
| `activities_activity` | every write | ❌ by design (audit log) |
| `ai_searchhistory` | every semantic search | ❌ |
| `knowledge_embeddingjob` | every upload and re-index | ❌ |
| `notifications_notification` | every notified event | ❌ |

The blacklist one is the most pressing: it grows fastest and is read on every
token validation.

---

## 3. Frontend performance

### What is fine

- **No re-render problems found.** `AuthProvider` and `WorkspaceProvider` both
  memoise their context values (`auth-provider.tsx:81-91`,
  `workspace-provider.tsx:69-85`), and `react-hook-form` keeps form state out of
  React state entirely.
- `refetchOnWindowFocus: false` prevents a refetch storm on tab switch.
- 60-second `staleTime` prevents refetching on every mount.
- Charts are hand-written SVG — no charting library in the bundle.

### What could bite

| Issue | Detail |
|---|---|
| **No list virtualisation** | Every list renders all 20 rows — fine at `PAGE_SIZE = 20`. Only becomes an issue if page size grows |
| **Everything is a Client Component** | Every `(app)` page is `"use client"`, so nothing is server-rendered and the whole tree ships to the browser. The trade-off is deliberate: pages need auth and workspace context |
| **`/search` fires four parallel list queries** | Projects, tasks, documents and handovers at once (`search/page.tsx`). Correct, but 4 round trips per keystroke-debounce |
| **Filter state is not in the URL** | Not a perf issue, but it means every navigation back to a list re-fetches from defaults |
| **No `next.config.ts` optimisation** | The config is an empty object. No `images`, no bundle analysis, no `output: "standalone"` (which would shrink the Docker image significantly) |

---

## 4. Scalability ceilings

### What scales horizontally today

| Component | Horizontal? | Condition |
|---|---|---|
| Django web (`uvicorn --workers 3`) | ✅ | Stateless — JWT, no server sessions for the API |
| Celery workers | ✅ | Add processes; Redis is the shared broker |
| WebSocket consumers | ✅ | **Only with the Redis channel layer.** The in-memory layer is per-process, so a push from worker A never reaches a socket on worker B |
| Throttling | ✅ | **Only with the Redis cache.** LocMem makes limits per-process |
| Next.js frontend | ✅ | Stateless |

The development settings switch both channels and cache to in-process
equivalents, so **a multi-process deploy must set `REDIS_URL`** — the
`development.py:40-42` comment says exactly this.

### What does not scale

| Limit | Why | Fix |
|---|---|---|
| **Local filesystem for uploads** | `MEDIA_ROOT` is a directory. Two web servers on different hosts do not share it | S3 via `django-storages` |
| **Database connections** | No pooling; `max_connections` becomes the ceiling | `CONN_MAX_AGE` or PgBouncer |
| **The embedding model in memory** | Each worker process holds ~90 MB+ of model. Compose limits `--concurrency=2` for this reason | A dedicated embedding service, or an API-based embedding provider |
| **Single PostgreSQL instance** | No read replica, no partitioning | Read replicas for analytics; partition `activities_activity` by month |
| **`_workspaces_being_deleted` is process-local** | A delete split across processes would not be protected | Would need a distributed flag, or a different approach entirely |
| **Analytics computed live** | Cost grows linearly with task count | Rollup tables |

### Rough capacity estimate

Not measured — reasoned from the code:

- Current shape (3 uvicorn workers, no pooling, ~15 queries per dashboard) should
  comfortably serve **tens of concurrent users**.
- The first thing to break under load is **database connections**, then the
  dashboard's query count.
- The first thing to break with data growth is the **document list N+1**, then
  the live analytics aggregation.

---

## 5. The fix order, if this had to scale tomorrow

1. `CONN_MAX_AGE = 60` — one line, immediate win.
2. Fix the document-list N+1 with `annotate` + `Prefetch`.
3. Collapse the dashboard's 10 counts into 2 aggregates.
4. Convert the three `source="...count"` fields to `annotate`.
5. Cache `/analytics/` for 5 minutes in Redis.
6. Schedule `flushexpiredtokens` with Celery beat.
7. Move uploads to S3 (also fixes the production media-serving gap).
8. Add composite indexes on `projects_project(workspace, status)` and
   `documents_document(workspace, project)`.
9. `StreamingHttpResponse` for the CSV export.
10. Replace the membership join + `DISTINCT` with a subquery.

Items 1–4 are a day's work and would roughly halve the query count of the three
most-used pages.

---

**Next:** [20 — Configuration & Environment](20-configuration-environment.md)
