# Interview — Advanced Questions (30)

[← Interviews index](README.md)

These go past "how does it work" into "why is it correct" and "where does it
break".

---

**1. Your permission classes only implement `has_object_permission`. What does
that mean for list endpoints?**
DRF calls `has_object_permission` from `get_object()` — detail routes only. It is
never called for `list` or `create`. So list safety comes entirely from
`get_queryset()` filtering, and create safety from `perform_create`'s explicit
membership check. All three exist, so the system is correct — but a new viewset
that relied on `permission_classes` alone for a list would protect nothing.

**2. `IsWorkspaceAdmin` and `IsWorkspaceManager` are defined but no view uses
them. Why?**
The equivalent logic is written inline in three places:
`HandoverViewSet._reviewer_membership`, `InvitationViewSet._is_admin`, and
`resolve_workspace(require_admin=True)`. Behaviour is consistent today; the risk
is drift — change `REVIEWER_ROLES` and three call sites must agree. The AI one
genuinely cannot use a permission class, because the workspace arrives in the
body.

**3. Why can't the AI endpoints use DRF object permissions?**
Object permissions run against an object fetched by `get_object()`. The AI action
endpoints receive the workspace id in the **request body**, so there is no object
to check. `resolve_workspace()` is the substitute, called before any retrieval.

**4. `resolve_workspace` returns 404 for a missing workspace and 403 for one you
are not in. Is that a problem?**
Yes, minor. Everywhere else in the API both cases return 404, so an authenticated
user can probe UUIDs to learn which workspaces exist. Low value given UUIDs are
unguessable, but it is an inconsistency. Raising `NotFound` in both branches
fixes it.

**5. Explain the workspace-deletion suppression guard.**
Deleting a workspace cascades into every child, and each cascade fires
`post_delete`, which would append activity rows referencing a workspace about to
disappear — a foreign-key violation at commit that takes the whole delete down.
`_workspaces_being_deleted` is a module-level set; `pre_delete` adds the pk,
`post_delete` removes it, and `log_activity` returns early while it is present.

**6. What is wrong with that approach?**
It is process-local mutable global state. It works because the delete and its
cascade happen inside one request in one process. It would not protect a delete
split across processes, and it is a shared mutable set. A cleaner fix would be to
check `Workspace.objects.filter(pk=...).exists()` before writing, or to disconnect
the receivers for the duration.

**7. Two concurrent requests both create a project called "Billing". What
happens?**
Both call `_generate_unique_slug`, both see `billing` free, both try to insert.
The unique constraint `unique_project_slug_per_workspace` rejects the second with
an `IntegrityError` — which nothing catches, so it surfaces as a 500. Data stays
correct; the error handling does not. A bounded retry loop on `IntegrityError`
would fix it.

**8. Where else could a race occur?**
Two pending handovers on one task, both approved in sequence — the second
silently overwrites the first's assignment. Registration with the same email
(caught by the unique constraint). Two reindexes of one document racing on
`unique_document_chunk_index` — though `_store_chunks` is atomic, so no partial
state.

**9. `HandoverViewSet.review` does two saves without a transaction. What could go
wrong?**
A crash between them leaves the handover marked approved but the task
unassigned — and the notifications are inconsistent with the data. It should be
`@transaction.atomic`. The notification pushes are already `on_commit`, so they
would correctly not fire on rollback.

**10. Why `update_fields` on those saves?**
It writes only the named columns, which avoids clobbering a concurrent update to
an unrelated field. `post_save` still fires, so the audit log still records it.

**11. Explain the single-flight refresh, and why it is a correctness fix rather
than an optimisation.**
`refreshPromise` is module scope; the first 401 creates the promise and the rest
await it. `.finally()` clears the slot either way. It is a correctness fix
because `ROTATE_REFRESH_TOKENS` + `BLACKLIST_AFTER_ROTATION` make the token
single-use — five parallel refreshes would blacklist each other's tokens and log
the user out.

**12. What guarantees the refresh retry terminates?**
`request()` recurses once with `_isRetry: true`, and the 401 branch is guarded on
`!_isRetry`. So at most one retry per request.

**13. `WorkspaceProvider` resolves the active workspace during render rather than
in an effect. Why?**
The code comment records the bug: two effects — one restoring the persisted id,
one validating it — could race, so the validator overwrote the restored id with
`workspaces[0]` because it still saw the pre-restore value. Deriving during render
eliminates the race by construction rather than by ordering effects correctly.

**14. Why does it need both `selectedId` state and `useSyncExternalStore`?**
A same-tab `localStorage.setItem` fires **no** `storage` event — that event only
fires in other tabs. So the in-tab choice needs its own state, and it takes
precedence over the stored value.

**15. What is the N+1 in the document serializer, and what does it cost?**
`get_embedding_status` runs `.order_by("-created_at").first()` and
`get_chunk_count` runs `.count()` — one query each, per row. A 20-document page
is 41 queries. The fix is `.annotate(Count("chunks"))` plus a `Prefetch` of the
jobs, which takes it to 3.

**16. Are there other N+1s?**
Three cheaper ones: `member_count`, `task_count` and `reply_count` all use
`source="...count"`, which is one query per row. Each converts to an `annotate`.

**17. The dashboard issues 15+ queries. How would you reduce it?**
Collapse the ten `.count()` calls into two `aggregate()` calls using
`Count("id", filter=Q(...))`, which PostgreSQL implements as
`COUNT(*) FILTER (WHERE ...)`. That takes it to about 7. Then cache the payload
for 30-60 seconds — the dashboard is not a real-time view.

**18. There is no connection pooling. What is the consequence?**
`CONN_MAX_AGE` is unset, so Django's default of 0 applies — every request opens
and closes a PostgreSQL connection. That is a TCP handshake and a backend fork
per request, and `max_connections` becomes the hard ceiling. `CONN_MAX_AGE = 60`
is the one-line fix; PgBouncer is the real answer beyond a few processes.

**19. Why HNSW rather than IVFFlat for the vector index?**
IVFFlat needs a training pass over existing data and degrades as new rows arrive
until it is re-trained. Documents here arrive one at a time, so HNSW — which is
incremental and needs no training — is the correct choice. The cost is higher
memory.

**20. What breaks if you switch to a 1536-dimension embedding provider?**
The pgvector column. `EMBEDDING_DIM` is baked in at migration time, so it needs a
migration altering `DocumentChunk.embedding` — and every existing embedding is
invalid and must be recomputed. `embeddings/factory.py` records the required
dimension per unimplemented provider precisely so the mistake is obvious.

**21. How do you defend against prompt injection, and what are the limits?**
Three mechanisms: `sanitize_input` strips control characters and caps length;
`wrap_untrusted` fences retrieved content in pseudo-XML; `SYSTEM_GUARDRAILS`
states at the highest priority that CONTEXT is data and never instructions. Plus
the real question comes **last**, so recency bias favours it.
The limits: prompt injection is not solved. The real containment is that
retrieval is workspace-scoped and the model has **no tools** — a successful
injection cannot reach another tenant or write anything.

**22. `action_items._parse` has six defensive layers. Why so many?**
Because the model's output is untrusted input. Regex out the array, `json.loads`
in a try, check it is a list, check each item is a dict with a title, coerce the
priority to a valid `TaskPriority`, null any malformed date, truncate the title.
`_VALID_PRIORITIES` is deliberately kept identical to `TaskPriority` so approved
suggestions are accepted by the existing create endpoint.

**23. The analytics "completed per week" is wrong. Explain.**
There is no `completed_at` column, so the view infers the week from `updated_at`.
Editing a task completed months ago moves it into the current week's bar. The
view's docstring admits it. The fix is a `completed_at` column set on the
transition into `completed`.

**24. Why is the weekly bucketing done in Python rather than SQL?**
`TruncWeek` + `GROUP BY` would return only weeks that have data, so you would
still need to fill gaps in Python. A pre-seeded dict does the whole thing in one
pass over a bounded 8-week window. At larger scale, SQL plus gap-filling wins —
the current version pulls every matching timestamp into Python.

**25. Why is `workspace_id` denormalised onto `DocumentChunk`?**
So the tenant boundary is a single indexed filter on the similarity query — the
hot path. Without it, every vector search would join through
`documents_document`.

**26. What happens to the vector search if pgvector is not installed?**
`CosineDistance` produces SQL PostgreSQL cannot execute, raising `DatabaseError`.
The AI views catch it and return a 503 with an actionable message rather than
leaking a 500.

**27. `Comment.author` is `CASCADE` while every other user FK is `SET_NULL`. What
is the impact?**
Deleting a user erases their comments, and via the `parent` cascade, other
people's replies underneath them. It is inconsistent with the rest of the schema
and destroys other users' content. `SET_NULL` would be the consistent choice.

**28. `Workspace.owner` is also `CASCADE`. Why is that worse?**
Deleting one user destroys every workspace they own and everything inside it —
projects, tasks, documents, handovers, embeddings. There is no ownership-orphan
path and no check blocking deletion of a user who owns workspaces.

**29. Which writes bypass your audit log, and does it matter?**
`queryset.update()`, `bulk_create`, raw SQL and direct database edits fire no
signals. Today only `read_all` on notifications uses `.update()`, and
notifications are not audited — so it does not matter yet. It is the pattern to
watch: an audit log that can be bypassed by an ORM idiom is a trap for the next
developer.

**30. If you had one day to improve this codebase, what would you do?**
`CONN_MAX_AGE`, `; Secure` on cookies, extend the proxy matcher, add
`app/error.tsx` plus `isError` branches, fix the document N+1, collapse the
dashboard counts, add upload size validation, and write `apps/tasks/tests.py`.
That removes both high-severity performance items, the worst reliability gap, two
security items and the most conspicuous testing hole.

---

**Next:** [Senior / architect questions](senior-architect-questions.md)
