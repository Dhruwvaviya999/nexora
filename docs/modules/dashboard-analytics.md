# Module — Dashboard & Analytics

[← Modules index](../12-business-modules.md) · [← Docs index](../README.md)

The only **read-only** module. It owns no table; it aggregates six other modules'
data.

---

## 1. The problem it solves

"What is the state of this workspace?" — answered two ways:

- **Dashboard** — ten counters plus four recent-item lists. The landing page.
- **Analytics** — chart-ready aggregates: an 8-week created-vs-completed series,
  status and priority breakdowns, per-member workload, and handover review
  metrics.

---

## 2. Frontend

| Route | File | Hook | Endpoint |
|---|---|---|---|
| `/dashboard` | `app/(app)/dashboard/page.tsx` | `useDashboard(id)` | `GET /dashboard/?workspace=` |
| `/analytics` | `app/(app)/analytics/page.tsx` | `useAnalytics(id)` | `GET /analytics/?workspace=` |

Both pages start with the same guard:

```ts
if (!wsLoading && !activeWorkspaceId) return <NoWorkspace />;
```

### Dashboard layout

Ten `StatCard`s, then four `Card` lists (recent projects, recent tasks, recent
documents, pending handovers), each with a "View all" link and an `EmptyState`
fallback.

Two cards get conditional accent colours:

```tsx
<StatCard label="Overdue" value={stats.overdue_tasks} icon={TriangleAlert}
  accent={stats.overdue_tasks ? "bg-destructive/15 text-destructive" : undefined} />
<StatCard label="Pending handovers" value={stats.pending_handovers} icon={ArrowLeftRight}
  accent={stats.pending_handovers ? "bg-amber-500/15 text-amber-600 dark:text-amber-400" : undefined} />
```
`dashboard/page.tsx:77-93` — zero is neutral, non-zero draws the eye.

Loading state is ten `<Skeleton className="h-24 rounded-xl"/>` in the same grid,
so the layout does not jump.

### Charts

`components/charts/charts.tsx` — **one file, hand-written SVG.** No charting
library is installed. The README notes the colours were validated for
colour-vision deficiency in both light and dark mode.

---

## 3. Backend

All three views live in `backend/apps/core/views.py`. `core` is not a domain — it
is "everything that isn't one". It also holds the `seed_demo` command and the two
broadest test files.

`core/views.py` imports models **and** serializers from six other apps:

```python
from apps.documents.models import Document
from apps.documents.serializers import DocumentSerializer
from apps.handovers.models import Handover, HandoverStatus
from apps.handovers.serializers import HandoverSerializer
from apps.projects.models import Project, ProjectStatus
from apps.projects.serializers import ProjectSerializer
from apps.tasks.models import Task, TaskStatus
from apps.tasks.serializers import TaskSerializer
from apps.workspaces.models import Workspace
```

That makes it the most coupled file in the backend — a deliberate trade for a
single-round-trip dashboard.

### The scoping guard

```python
def _workspace_or_404(request):
    workspace_id = request.query_params.get("workspace")
    if not workspace_id:
        raise ValidationError({"workspace": "This query parameter is required."})
    return get_object_or_404(
        Workspace.objects.filter(members__user=request.user).distinct(), pk=workspace_id)
```
`core/views.py:154-161`

The membership filter is **inside** `get_object_or_404`, so a non-member gets
**404**, not 403 — the same "don't confirm the id exists" property as the scoped
viewsets. `DashboardView` inlines the identical pattern.

---

## 4. Dashboard stats — the definitions

```python
OPEN_TASK_STATUSES = (TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.REVIEW)
```

| Stat | Definition |
|---|---|
| `total_projects` | all projects in the workspace |
| `active_projects` | `status=active` **and** `archived=False` |
| `archived_projects` | `archived=True` |
| `total_tasks` | all |
| `pending_tasks` | status in `OPEN_TASK_STATUSES` |
| `completed_tasks` | `status=completed` |
| `overdue_tasks` | **open and `due_date < today`** |
| `total_documents` | all |
| `my_tasks` | open **and** `assignee = request.user` |
| `pending_handovers` | `status=pending` in the workspace |

Two things to remember:

- A completed task with a past due date is **not** overdue.
- `pending_handovers` is workspace-wide, **not** filtered to handovers you can
  review — a plain member sees a count they cannot act on.

Then four `[:5]` lists, each serialised with `select_related` on its own view:

```python
"recent_projects":  ProjectSerializer(projects.select_related("owner","created_by")[:5], ...)
"recent_tasks":     TaskSerializer(tasks.select_related("project","assignee")[:5], ...)
"recent_documents": DocumentSerializer(documents.select_related("uploaded_by")[:5], ...)
"pending_handovers": HandoverSerializer(handovers.filter(status=PENDING)
                        .select_related("task","from_user","to_user")[:5], ...)
```

`ctx = {"request": request}` is passed so `DocumentSerializer.get_file_url` can
build absolute URLs.

---

## 5. Analytics — the definitions

`AnalyticsView.get()` returns five keys.

### `task_status` and `task_priority`

```python
[{"status": row["status"], "count": row["count"]}
 for row in tasks.values("status").annotate(count=Count("id"))]
```
Two `GROUP BY` queries.

### `weekly` — the 8-week series

```python
today        = timezone.now().date()
this_monday  = today - timedelta(days=today.weekday())
week_starts  = [this_monday - timedelta(weeks=i) for i in range(7, -1, -1)]   # oldest first
window_start = week_starts[0]

def _bucket(dates):
    counts = {ws: 0 for ws in week_starts}      # pre-seeded → no missing weeks
    for d in dates:
        monday = d - timedelta(days=d.weekday())
        if monday in counts: counts[monday] += 1
    return counts
```

Pre-seeding all eight keys means quiet weeks appear as zeros rather than gaps.
Explained in [14-algorithms.md](../14-algorithms.md#6-weekly-bucketing-for-analytics).

**The known approximation.** The view's own docstring:

> "Completed" per week counts tasks whose status is completed by their last
> update in that week (the model has no dedicated `completed_at` column).

So editing a task completed months ago moves it into this week's bar. Documented,
not hidden — but it should be fixed with a `completed_at` column.

### `workload`

Top 8 assignees by count of **open** tasks:

```python
tasks.filter(assignee__isnull=False, status__in=OPEN_TASK_STATUSES)
     .values("assignee_id", "assignee__name", "assignee__email")
     .annotate(count=Count("id")).order_by("-count")[:8]
```

Name falls back to email — matching `_display()` elsewhere in the codebase.

### `handovers`

```python
reviewed   = handovers.filter(reviewed_at__isnull=False)
avg_review = reviewed.annotate(wait=F("reviewed_at") - F("created_at")).aggregate(avg=Avg("wait"))["avg"]
{
  "pending":  ..., "approved": ..., "rejected": ...,
  "avg_review_hours": round(avg_review.total_seconds()/3600, 1) if avg_review else None,
}
```

`F("reviewed_at") - F("created_at")` computes the interval **in the database**,
and `Avg` over a duration works because PostgreSQL has a real `interval` type.
`None` when nothing has been reviewed — the frontend must handle that.

---

## 6. API

| Method | Endpoint | Auth | Required param |
|---|---|---|---|
| GET | `/health/` | **public** (`AllowAny`, `authentication_classes = []`) | — |
| GET | `/dashboard/` | member | `?workspace=<uuid>` |
| GET | `/analytics/` | member | `?workspace=<uuid>` |

Both use `serializer_class` (`DashboardSerializer`, `AnalyticsSerializer`) purely
so drf-spectacular can document the response shape — the views build their
payloads as plain dicts.

Detail: [api/core.md](../api/core.md).

---

## 7. Health check

```python
class HealthCheckView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []          # ← no auth machinery at all

    def get(self, request):
        try: connection.ensure_connection(); database_ok = True
        except Exception: database_ok = False
        return Response({"status": "ok" if database_ok else "degraded",
                         "service": "ai-knowledge-workflow-assistant",
                         "version": "v1",
                         "database": "ok" if database_ok else "unavailable"},
                        status=200 if database_ok else 503)
```

Public *on purpose*, per the docstring, so uptime monitors and orchestrators can
reach it without a token. It is the `web` service's Docker healthcheck.

Note both `permission_classes = [AllowAny]` **and** `authentication_classes = []`
— the second means a malformed `Authorization` header cannot make the health
check fail.

---

## 8. Performance

The dashboard fires **15+ queries**: ten `.count()` calls plus four list queries,
and `DocumentSerializer` adds two more per document row.

It is the first screen every user loads, so it is the highest-value optimisation
in the project:

```python
tasks.aggregate(
    total     = Count("id"),
    pending   = Count("id", filter=Q(status__in=OPEN_TASK_STATUSES)),
    completed = Count("id", filter=Q(status=TaskStatus.COMPLETED)),
    overdue   = Count("id", filter=Q(due_date__lt=today, status__in=OPEN_TASK_STATUSES)),
    mine      = Count("id", filter=Q(assignee=request.user, status__in=OPEN_TASK_STATUSES)),
)
```

Five queries become one. Same treatment for projects takes the total from 15+ to
about 7.

Analytics recomputes everything live on every request — fine at demo scale, worth
caching for 5-15 minutes as data grows. Full analysis in
[19-performance-scalability.md](../19-performance-scalability.md).

---

## 9. Failure scenarios

| Scenario | Result |
|---|---|
| No `?workspace=` | 400 `{"workspace": ["This query parameter is required."]}` |
| Workspace you are not in | **404** |
| Workspace with no data | All zeros, empty lists, `avg_review_hours: null`; the UI shows `EmptyState` |
| No handovers reviewed yet | `avg_review_hours: null` |
| Database down | `/health/` returns 503; dashboard and analytics 500 |
| User belongs to no workspace | `activeWorkspaceId` is null; the page renders `<NoWorkspace/>` and never calls the API |

---

## 10. Dependencies

**Depends on:** projects, tasks, documents, handovers, workspaces — models *and*
serializers.

**Depended on by:** nothing. It is a leaf, read-only module.

**The consequence:** any serializer change in those five apps changes the
dashboard response. `DocumentSerializer` adding a `SerializerMethodField` made
the dashboard slower without anyone touching `core`.

---

## 11. Interview questions

1. Why is `/dashboard/` one endpoint instead of the frontend calling five?
   *(One round trip on the landing page. Cost: `core` is coupled to six apps.)*
2. How is "overdue" defined, and why is it defined in one place?
3. Why does a non-member get 404 rather than 403 here?
4. How many queries does the dashboard run, and how would you reduce it?
5. Explain the weekly bucketing. Why pre-seed the dict?
6. Why is "completed this week" an approximation? How would you fix it properly?
7. `avg_review_hours` uses `F("reviewed_at") - F("created_at")`. Where does that
   subtraction happen? *(In PostgreSQL, as an `interval` — not in Python.)*
8. Why is the health check `authentication_classes = []` as well as `AllowAny`?
9. `core/views.py` imports from six apps. Is that a problem?
   *(It is the aggregation seam. Acceptable for a read-only view; it would be a
   problem if `core` also wrote.)*
10. How would you make analytics scale to a million tasks per workspace?
    *(Cache it, push bucketing into SQL with `TruncWeek`, or maintain a rollup
    table updated on write.)*
