# Interview — Intermediate Questions (30)

[← Interviews index](README.md)

---

**1. Walk me through what happens when someone logs in.**
The form validates with zod, then `AuthProvider.login()` calls
`authApi.login()` → `apiClient.post("/auth/login/", data, {skipAuth: true})`.
Django routes to `LoginView`, throttled at 10/min per IP.
`EmailTokenObtainPairSerializer` validates the credentials via its parent, then
adds the user object to the response. The client stores both tokens in cookies
and sets `user` in context. No `/auth/me/` call is needed on this path.

**2. Why does the login response include the user object?**
`EmailTokenObtainPairSerializer` adds five lines to include it. That saves a
follow-up `/auth/me/` request on every login. `/auth/me/` is only used on page
reload, when the cookie exists but the JS heap is empty.

**3. Explain the token refresh mechanism.**
`client.ts` catches a 401, calls `getRefreshedToken()`, and retries once with
`_isRetry: true` so it cannot loop. `refreshPromise` is a **module-level**
variable, so ten concurrent 401s share one in-flight refresh. That is necessary,
not just an optimisation — `ROTATE_REFRESH_TOKENS` plus
`BLACKLIST_AFTER_ROTATION` make a refresh token single-use, so parallel
refreshes would blacklist each other's tokens.

**4. What are the three layers of route protection?**
`src/proxy.ts` at the edge (cookie presence only, and only for
`/dashboard/*`, `/workspaces/*`, `/login`, `/register`);
`app/(app)/layout.tsx` client-side (redirects if `!isAuthenticated`); and DRF
permissions on the server. **Only the third is a security boundary.**

**5. Why does a cross-tenant request return 404 instead of 403?**
`WorkspaceScopedViewSet.get_queryset()` filters by membership, so the row is
never in the queryset and `get_object()` raises `Http404`. That is better than
403 — it does not confirm the id exists.

**6. How does `WorkspaceScopedViewSet` work?**
`get_queryset()` filters `workspace__members__user=request.user` with
`.distinct()`. `perform_create` checks membership explicitly and stamps
`created_by`/`updated_by`. `perform_update` stamps `updated_by`. Subclasses then
declare only their serializer, filterset and search/ordering fields — which is
why `apps/tasks/views.py` is 25 lines.

**7. Why is `.distinct()` needed there?**
The join through the membership table can duplicate rows. The unique constraint
means it should not in practice, but the ORM cannot know that.

**8. Why is `workspace` read-only on `TaskSerializer`?**
It is derived from the project inside `validate()`. Without that, a client could
post a project from tenant A while claiming workspace B, and poison every scoped
query.

**9. How do you validate that an assignee is allowed?**
`_resolve_member()` queries `workspace.members.filter(user_id=...)`. A valid user
UUID is not enough — there must be a membership row in that workspace.

**10. Explain the `assignee` / `assignee_id` split.**
`assignee` is a nested `UserSerializer`, read-only. `assignee_id` is a write-only
UUID. The client sends an id; the response carries the full user object so the UI
can render an avatar without another request.

**11. What happens when a handover is approved?**
Status, reviewer, comment and `reviewed_at` are written; then
`task.assignee = handover.to_user`; then two notifications — `TASK_ASSIGNED` to
the recipient and `HANDOVER_REVIEWED` to the submitter. Two audit rows are
written by signals, and the frontend invalidates three query keys.

**12. Why is that the only cross-module write?**
Because approval is the *authorisation point*. The assignment is a consequence of
a decision, not an action someone could take without review.

**13. How is the audit log written?**
Entirely by signal receivers registered in `ActivitiesConfig.ready()`. A factory
function wires `post_save` and `post_delete` per model, so adding history for a
new model is one line. No domain app imports `activities`.

**14. What does the audit log miss?**
Anything that bypasses `post_save`: `queryset.update()`, `bulk_create`, raw SQL,
psql. `NotificationViewSet.read_all` uses `.update()` deliberately.

**15. Why `weak=False` on the signal connections?**
The handler closures are created inside a factory function and referenced nowhere
else, so Python would garbage-collect them and the signals would silently stop
firing.

**16. What is `dispatch_uid` for?**
It prevents double registration if the handlers module is imported twice — which
would double every audit row.

**17. How does @mention detection work?**
The frontend emits `@[Display Name](<user-uuid>)`. A regex in
`apps/mentions/services.py` extracts the UUIDs, filters them to workspace members
excluding the author, and reconciles `Mention` rows — adding new ones, deleting
ones removed by an edit, and firing `user_mentioned` **only for genuinely new
mentions**, so editing does not re-notify.

**18. Why does `mentions` emit a custom signal instead of calling
`create_notification`?**
So `mentions` does not import `notifications`. It publishes a domain event;
whoever cares subscribes. Today `notifications/handlers.py` is the only
subscriber.

**19. Why is comment delete soft?**
So reply chains stay intact. It sets `is_deleted=True` **and blanks the
content**, and `to_representation` returns `"[deleted]"`. Blanking the content
also clears the comment's mentions on the next sync.

**20. Explain the document upload path.**
The form builds a `FormData`; `apiClient` detects it and omits `Content-Type` so
the browser sets the multipart boundary. DRF's `MultiPartParser` handles it; the
serializer captures `file_size`, `file_type`, `uploaded_by` and a default title.
A `post_save` signal creates an `EmbeddingJob` and queues a Celery task **after
commit**. The 201 returns immediately.

**21. Why `transaction.on_commit` before queueing?**
Queueing inside the transaction races the worker — it could read a document row
that is not visible yet, or act on one that rolled back. The same pattern is used
for email and websocket pushes.

**22. What happens if the Celery broker is down?**
`.delay()` throws, the code catches it, logs, and runs the job inline. The
comment says "better slow than lost."

**23. How does semantic search stay inside a workspace?**
`semantic_search()` filters `workspace=workspace` **before** the vector ordering.
`workspace_id` is denormalised onto `DocumentChunk` specifically so that filter
is a single indexed predicate on the hot path.

**24. Why 384 dimensions?**
That is the output size of `all-MiniLM-L6-v2`, the local embedding model. It is
baked into the pgvector column at migration time, so changing providers requires
a migration.

**25. What is the confidence score?**
`1 - cosine_distance` of the best-matching chunk, bucketed: ≥0.6 high, ≥0.4 or
structured context present medium, else low. It tells the user how much of the
answer was actually grounded in their documents.

**26. Why are AI-generated tasks not saved automatically?**
The model never writes to the database. Suggestions are returned for review and
created through the normal Task API, so they pass the same validation as a
manually created task. A hallucinated task cannot silently appear in someone's
list.

**27. What does the websocket actually send?**
A signal, not data — `{"type": "notification"}`. The client uses it to invalidate
the React Query cache and refetch over REST. One source of truth, no cache drift.

**28. Why is the websocket token in the query string?**
The browser `WebSocket` API cannot set an `Authorization` header. The mitigations
are wss in production and a 15-minute token lifetime, both documented in
`channels_auth.py`.

**29. What does `queryClient.clear()` in logout prevent?**
The next person to sign in on that browser briefly seeing the previous user's
cached lists before the refetches land.

**30. How does the app behave with no Redis?**
Celery tasks run inline, the channel layer is in-process (so websockets work with
one process), and throttle counters live in local memory. Development is designed
to need nothing but PostgreSQL.

---

## Trace-it exercises

Say these out loud with real file names.

1. `/tasks` page load → `GET /api/v1/tasks/`
2. Submitting a handover, including both side effects
3. A comment with an @mention → a badge updating without a refresh
4. Upload → chunk row in the database
5. A 401 → silent refresh → the original request succeeding

---

**Next:** [Advanced questions](advanced-questions.md)
