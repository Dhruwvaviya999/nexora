# Interview — Scenario Questions (20)

[← Interviews index](README.md)

"How would you…" — these test whether you actually understand your own
architecture well enough to extend it.

---

**1. Add a "task comments must be approved by a manager" feature.**
Add `is_approved` and `approved_by` to `Comment`, default `False` for members.
Add an `@action(detail=True, methods=["post"]) def approve` on `CommentViewSet`,
guarded by `REVIEWER_ROLES` — I would use the existing `IsWorkspaceManager` class
rather than another inline check. Filter unapproved comments out of
`get_queryset` for non-reviewers. Register the new action in
`activities/handlers.py` for audit. Frontend: a badge and an approve button gated
on `activeWorkspace.role`.

**2. Add file attachments to comments.**
A new `CommentAttachment` model with a `comment` FK and a `FileField`, following
`Document`'s upload-path pattern. `CommentViewSet` needs `parser_classes` for
multipart. **Before shipping it I would fix the upload gap first** — size limit,
extension whitelist, `Content-Disposition: attachment` — because adding a second
upload surface with the same weaknesses doubles the exposure.

**3. Support @mentions in task descriptions, not just comments.**
The mention machinery is already decoupled — `sync_comment_mentions` just needs
generalising to `sync_mentions(obj, text_field, workspace, author)`. Add a
`post_save` receiver on `Task`. The `Mention` model would need a generic FK
instead of a `comment` FK, matching what `Comment` and `Activity` already do. The
notification handler needs no change, because it listens to the signal.

**4. Add a "watch this task" feature so people get notified of any change.**
A `TaskWatcher` through-table. Then a receiver on `Task` `post_save` that calls
`create_notification` for each watcher — reusing `TASK_UPDATED`, which is already
defined in the enum and currently never emitted. `create_notification` already
skips self-notification, so the actor is excluded for free.
The thing to be careful about: `queryset.update()` fires no signal, so any bulk
status change would silently skip notifications.

**5. Let users set a per-workspace notification preference.**
A `NotificationPreference` model keyed on (user, workspace, type). The check
belongs inside `create_notification` — it is the single choke point, with six call
sites, so one `if` there covers every notification in the system. That is the
payoff of having a service function instead of inline `Notification.objects.create`.

**6. Add task dependencies — "this blocks that".**
A self-referential M2M on `Task` with a through-table, or a separate
`TaskDependency` model with `blocks`/`blocked_by`. The interesting part is cycle
detection: I would validate in the serializer with a depth-limited graph walk.
And the dashboard's `pending_tasks` would probably want to distinguish "blocked"
from "open".

**7. Support recurring tasks.**
A `RecurrenceRule` on `Task` plus a **Celery beat schedule** — which does not
exist yet; there is no beat service at all. That is the real work: adding a
scheduler, which I also want for `flushexpiredtokens`. The task itself clones the
template task on each occurrence.

**8. Let a workspace bring its own S3 bucket.**
This is harder than it looks. `STORAGES` is global Django configuration, not
per-request. I would need a custom storage backend that resolves the bucket from
the instance's workspace, plus per-workspace credentials encrypted the way
`AISettings.api_key` already is — `services/crypto.py` is directly reusable.

**9. Add real-time collaborative editing to task descriptions.**
Out of scope for the current architecture. The websocket layer is deliberately
**push-only** and carries no data the client trusts. Collaborative editing needs
bidirectional messages, operational transforms or CRDTs, and per-document channel
groups. I would use a purpose-built service (Yjs) rather than extending this
consumer — and I would say so rather than pretending it is a small change.

**10. Support 100 concurrent AI chats.**
The LLM call is the bottleneck and it is synchronous — it holds a uvicorn worker
for its whole duration. Three steps: move the LLM call to a Celery task and
return a job id the client polls; or implement SSE streaming, for which
`BaseLLMProvider.stream()` is **already written** and unused; and raise
`THROTTLE_AI` deliberately with cost monitoring, since 100 concurrent chats is
real money.

**11. Add an "export all workspace data" feature (GDPR).**
A Celery task that walks every workspace-scoped model, serialises to JSON, writes
a zip to storage, and emails a link. The tenancy model makes this
straightforward — every table has `workspace_id`. The awkward parts are the
generic relations (comments and activities need `content_type` resolution) and
uploaded files.

**12. Support workspace-level data deletion with a 30-day grace period.**
A `deleted_at` on `Workspace` plus filtering it out of every queryset — which
means touching `WorkspaceScopedViewSet.get_queryset()`, the one place that
matters. Then a beat task that hard-deletes after 30 days. Note the existing
`_workspaces_being_deleted` suppression guard would still apply at hard-delete
time.

**13. Add SSO / SAML.**
`django-allauth` or `python-social-auth`, issuing the same JWT pair on success so
nothing downstream changes. The interesting decision is provisioning: does an SSO
login auto-create a workspace membership? I would map an IdP group to a
`WorkspaceRole` and reconcile on each login.

**14. A customer wants their data in a separate database.**
That is the schema-per-tenant or database-per-tenant conversation. With the
current `workspace_id` design, the cheapest path is a separate **deployment**, not
a database router — routers would have to be threaded through every query and the
membership join would break. I would price it as a dedicated instance rather than
retrofitting the isolation model.

**15. Add full-text search across everything.**
Today `/search` fires four parallel list queries with `?search=`, each producing
leading-wildcard `ILIKE`. I would move to PostgreSQL full-text: a `SearchVector`
column per searchable model with a GIN index, updated by trigger or on save. Or —
more interestingly — reuse the existing embedding pipeline for semantic search
over tasks and projects, not just documents.

**16. The AI is answering from another workspace's documents. Debug it.**
That would be a serious bug, so I would verify it is real before anything else.
Check `DocumentChunk.workspace_id` for the returned chunks — if it is wrong, the
denormalisation is broken at write time in `_store_chunks`. If it is right, then
`semantic_search`'s filter was bypassed, or `resolve_workspace` returned the
wrong workspace. I would add a test asserting that retrieval never returns another
workspace's chunks — which does not currently exist.

**17. Support offline mode.**
Substantial. `persistQueryClient` with IndexedDB for reads, a mutation queue for
writes, and a service worker. The hard part is conflict resolution, and the schema
has no version column or `updated_at` comparison on write — so today it is
last-write-wins. I would add optimistic locking first.

**18. Add a mobile app.**
The API is ready — it is JSON, JWT-authenticated, versioned and documented with
OpenAPI. Three changes: refresh tokens in secure device storage rather than
cookies (which actually removes the httpOnly problem), the websocket URL needs
the token in the query string as it already does, and push notifications would
need a device-token table and FCM/APNs alongside `create_notification`.

**19. A user reports the dashboard is slow. What do you do?**
Measure first. `assertNumQueries` or `connection.queries` around
`GET /dashboard/`. I already know the answer — 15+ queries, ten of them separate
`COUNT`s — so I would collapse them into two `aggregate()` calls with
`Count("id", filter=Q(...))`, then add a 30-60 second Redis cache keyed on
(workspace, user). Then verify with the same query count assertion so it cannot
regress.

**20. Your CEO wants an "AI writes my status report" button by Friday.**
Most of it exists. `summarize` already accepts `target_type="activity"` with a
period, gathers up to 200 activity rows, and returns a markdown summary. The work
is a frontend button, a period selector, and possibly scoping to *my* activity
rather than the whole workspace — one extra filter in `_gather_activity`.
The thing I would push back on is cost and rate limits: `AIRateThrottle` is
30/hour per user, and a report over 200 activity rows is a large prompt.

---

## The pattern behind good answers here

1. **Name the existing code you would extend**, not a generic approach.
2. **Identify the choke point** — `create_notification`, `get_queryset`,
   `WorkspaceScopedViewSet` — where one change covers everything.
3. **Say what would be hard**, and why.
4. **Push back when the architecture genuinely does not fit** (questions 9, 14,
   17). Saying "that's a different system" is a better answer than pretending.

---

**Next:** [Debugging scenarios](debugging-questions.md)
