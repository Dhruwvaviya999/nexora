# Interview — Backend Questions (20)

[← Interviews index](README.md)

---

**1. How is the backend organised?**
One Django app per domain under `backend/apps/`, plus `apps/common` holding the
shared foundation — abstract models, permission classes, the scoped viewset,
throttles, email and websocket auth. `config/` holds settings, URLs, ASGI and
Celery. Each domain app is the same five files: models, serializers, filters,
views, urls.

**2. What does `apps/common` contain and why does it matter?**
The four abstract base models (`TimeStampedModel`, `UUIDModel`, `BaseModel`,
`AuditModel`, `WorkspaceScopedModel`), five permission classes, and
`WorkspaceScopedViewSet`. Change any of them and every model or endpoint in the
project changes. It is the reason `apps/tasks/views.py` is 25 lines.

**3. Explain the abstract model hierarchy.**
`UUIDModel` gives a UUID primary key — non-sequential, safe to expose in URLs.
`TimeStampedModel` gives `created_at`/`updated_at`. `BaseModel` combines them.
`AuditModel` adds `created_by`/`updated_by` with `related_name="+"` so a dozen
models can share FKs to `User` without clashing. `WorkspaceScopedModel` adds the
workspace FK with `related_name="%(class)ss"`, which auto-generates
`workspace.projects`, `.tasks`, `.documents`.

**4. Why UUID primary keys?**
Safe to expose — no enumerable sequential ids. Also generated client-side before
insert, and collision-free when merging environments. The cost is 16 bytes versus
4, and poor B-tree locality on insert, which is why everything orders by
`-created_at` rather than by id.

**5. Walk me through `WorkspaceScopedViewSet`.**
`permission_classes = [IsAuthenticated, IsWorkspaceMember]`;
`get_queryset()` filters `workspace__members__user=request.user` with
`.distinct()`; `perform_create` calls `_require_membership()` then stamps
`created_by`/`updated_by`; `perform_update` stamps `updated_by`. It also returns
an empty queryset when `swagger_fake_view` is set, because there is no
authenticated user during OpenAPI schema generation.

**6. Why does the DRF config matter so much here?**
`DEFAULT_PERMISSION_CLASSES = (IsAuthenticated,)` means **everything is private by
default** — only four views opt out. `DEFAULT_AUTHENTICATION_CLASSES` is JWT only,
so no session cookie will authenticate an API call. And the three filter backends
give every list view `?search=`, `?ordering=` and FilterSet fields for free.

**7. How do you handle filtering?**
`django-filter` `FilterSet` classes per app for simple model fields, with custom
declarations where the model has no such field — `due_before`/`due_after` map to
`due_date__lte`/`gte`, and the handover `project` filter maps to
`task__project_id`. Four apps hand-roll filtering in `get_queryset` instead —
comments, notifications, activities, invitations — where the filters are not
simple field lookups.

**8. Where does business logic live?**
It depends on the shape. Field-level and cross-field rules live in serializers
(`TaskSerializer.validate` derives the workspace and checks membership).
Action-level rules live in views (`HandoverViewSet.review`). Reusable operations
live in service modules — `activities/services.py`, `notifications/services.py`,
`mentions/services.py`, `knowledge/services/*`, `ai/services/*`. There is
deliberately no service layer for projects and tasks, because they are CRUD and it
would be a pass-through.

**9. Explain the signals architecture.**
Four handler modules, registered in `AppConfig.ready()`. `activities` writes the
audit log on `post_save`/`post_delete` for seven models — via a factory function,
so adding a model is one line. `mentions` re-syncs mention rows on comment save.
`notifications` listens for a custom `user_mentioned` signal and for comment
replies. `knowledge` queues embedding on document creation.
**No domain app imports `activities`** — that is the point.

**10. What are the downsides of signals, and how do you defend the choice?**
They are implicit — reading `TaskViewSet` gives no hint that saving writes an
audit row. And they have a blind spot: `queryset.update()`, `bulk_create` and raw
SQL fire nothing. I defend it at this size because the alternative is calling
`log_activity` in about fifteen places, where one omission is a silent gap. At ten
times the size I would want explicit service calls for anything a reader must
see.

**11. Why do some imports live inside functions?**
Three deliberate cycle-breaks. `apps/common/permissions.py` imports `Workspace`
inside each function because `workspaces` depends on `common`.
`notifications/services.py` imports the consumer inside `_push()` so the module
loads without Channels. `knowledge/services/processor.py` imports `tasks` inside
`dispatch()` because `tasks` imports `processor`. Plus lazy SDK imports in the LLM
providers, so a missing package is a clean `ProviderError` rather than an
import-time crash.

**12. How does the ASGI setup work?**
`config/asgi.py` builds a `ProtocolTypeRouter`: HTTP goes to the normal Django
application, `/ws/` goes to Channels behind an `OriginValidator` and a JWT
middleware. `get_asgi_application()` must be called **before** importing anything
that touches models, because it populates the app registry.

**13. Why validate the websocket Origin against `CORS_ALLOWED_ORIGINS` rather
than `ALLOWED_HOSTS`?**
The Origin on a websocket handshake is the **frontend's**, while `ALLOWED_HOSTS`
lists the **API's** hostnames. They coincide only while both run on localhost —
split them across `api.example.com` and `app.example.com` and
`AllowedHostsOriginValidator` would deny every socket.

**14. How does Celery integrate?**
`config/celery.py` creates the app and autodiscovers `tasks.py` in every app; it
is imported from `config/__init__.py` so `@shared_task` binds correctly however
the process started. Two tasks: `send_email_task` (3 retries, backoff) and
`process_document_task` (2 retries). Both are dispatched with
`transaction.on_commit`, and both fall back to running inline if the broker is
unreachable.

**15. Why `transaction.on_commit` rather than queueing immediately?**
Queueing inside the transaction races the worker: it can pick up the job and read
a row that is not visible yet, or act on a transaction that rolls back. Both the
processor and the email helper document exactly that reasoning.

**16. Explain the throttling setup.**
Six named scopes, all env-tunable. Credential endpoints (`login`, `register`,
`password_reset`) are keyed by **IP, not user** — the point is to limit an
attacker with no account, who would otherwise get a fresh bucket per guessed
email. Password reset deliberately does not key on the submitted address, because
that would let someone lock a specific person out of resets. AI is 30/hour per
user because LLM calls cost money.

**17. Why do the counters need Redis in production?**
DRF counts requests in the Django cache. With the default per-process
`LocMemCache`, each worker keeps a private counter, so the effective limit becomes
`rate × worker_count`. The settings comment says exactly this.

**18. How is the email system built?**
`common/email.py` renders `templates/email/<name>.txt` plus an optional `.html`
sibling. The plain-text body renders through a **second Django template engine**
named `"text"` with autoescaping off — because with escaping on, an `&` in a reset
URL becomes `&amp;` and the link arrives with a parameter literally named
`amp;token`. That engine must come *after* the default one, because
`django.contrib.admin`'s system checks inspect the first `DjangoTemplates` engine.

**19. How do the settings modules differ?**
`base.py` holds everything, reading from the environment. `development.py` turns
on DEBUG and the browsable API and — importantly — falls back to console email,
eager Celery, an in-memory channel layer and a locmem cache, so local development
needs nothing but Postgres. `production.py` forces DEBUG off, JSON-only rendering,
SSL redirect, HSTS and secure cookies. `test.py` removes every external service,
**disables throttling by setting each rate to `None`** (clearing the classes is
not enough, because the auth views name their throttles explicitly), and swaps in
the MD5 hasher for speed.

**20. What would you change on the backend?**
Wrap `HandoverViewSet.review` in a transaction. Set `CONN_MAX_AGE`. Use the two
unused permission classes instead of three inline role checks. Fix the document
serializer N+1 and the three `source="...count"` fields. Add a `completed_at`
column. Add a Celery beat schedule so `flushexpiredtokens` actually runs. And
write the empty test files — especially `apps/common/tests.py`, since it covers
the most security-critical class in the project.

---

**Next:** [Database questions](database-questions.md)
