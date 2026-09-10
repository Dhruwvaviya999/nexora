# Learning Roadmap — Master Your Own Project

[← Docs index](README.md)

Ten stages. Each has files to read, concepts to understand, questions to answer,
and a clear "you're done when…" test.

Total time if you do it properly: **12–16 hours**. You can do stages 1–4 in one
evening and get 70% of the value.

---

## Stage 1 — The Big Picture

**Time:** 45 minutes

**Read**
1. [project-cheat-sheet.md](project-cheat-sheet.md)
2. [01-project-overview.md](01-project-overview.md)
3. [02-system-architecture.md](02-system-architecture.md)
4. Skim [03-folder-structure.md](03-folder-structure.md)

**Open**
- `README.md` (root)
- `docker-compose.yml`
- `backend/config/urls.py`
- `frontend/src/lib/constants.ts`

**Concepts**
- Multi-tenancy: what a workspace *is*, and why everything hangs off it
- The 16 layers, and that only three of them enforce security
- Why this is a monolith and where the natural split would be

**Answer these**
1. What problem does the handover feature solve?
2. Which layers exist between a button click and a SQL query?
3. Which four things run as separate processes in Docker?
4. What is the only hard dependency?

**Done when:** you can draw the [60-second whiteboard diagram](interviews/whiteboard.md#the-60-second-version-if-thats-all-you-get)
from memory.

---

## Stage 2 — The Frontend

**Time:** 90 minutes

**Read**
1. [04-frontend-architecture.md](04-frontend-architecture.md)
2. [06-routing.md](06-routing.md)
3. [16-state-management.md](16-state-management.md)

**Open, in this order**
```
frontend/src/proxy.ts
frontend/src/app/layout.tsx
frontend/src/app/providers.tsx
frontend/src/app/(app)/layout.tsx
frontend/src/providers/auth-provider.tsx
frontend/src/providers/workspace-provider.tsx     ← read the comments carefully
frontend/src/app/(app)/dashboard/page.tsx
frontend/src/hooks/use-tasks.ts
```

**Concepts**
- Route groups `(auth)` / `(app)` and why they exist
- Provider composition, and why `WorkspaceProvider` is nested inside `(app)`
- TanStack Query keys, and why workspace-in-the-key means free refetching
- "Derive, don't sync" — the race that `workspace-provider` fixes

**Answer these**
1. Which file runs first for `/dashboard`, and what does it check?
2. Why is `WorkspaceProvider` not in `app/providers.tsx`?
3. What happens to every query when you switch workspace? Why?
4. Why does `workspace-provider` need both `selectedId` and `useSyncExternalStore`?
5. Where is form state kept, and why not `useState`?

**Done when:** you can explain, without looking, what happens between typing
`/tasks` in the address bar and seeing rows.

---

## Stage 3 — The API Layer

**Time:** 60 minutes

**Read**
1. [07-api-architecture.md](07-api-architecture.md)
2. [api/README.md](api/README.md)

**Open**
```
frontend/src/lib/api/client.ts        ← the whole file, twice
frontend/src/lib/api/errors.ts
frontend/src/lib/api/tasks.ts
frontend/src/lib/api/download.ts
frontend/src/lib/auth/token-storage.ts
```

**Do this:** open `/api/docs/` with the server running and call three endpoints.

**Concepts**
- Single-flight promise coalescing, and why it is a correctness fix
- Why FormData must not get a `Content-Type`
- Error normalisation, and `applyFieldErrors` as the bridge to react-hook-form

**Answer these**
1. What happens when ten requests get a 401 at once?
2. What guarantees the refresh retry terminates?
3. Why does `downloadFile` exist instead of using `apiClient`?
4. How does a DRF field error end up under the right input?

**Done when:** you can write the single-flight refresh from memory on a
whiteboard.

---

## Stage 4 — The Backend Core

**Time:** 2 hours

**Read**
1. [05-backend-architecture.md](05-backend-architecture.md)
2. [12-business-modules.md](12-business-modules.md)

**Open, in this order**
```
backend/config/settings/base.py          ← skim, but read the comments
backend/config/urls.py
backend/apps/common/models.py            ⭐
backend/apps/common/viewsets.py          ⭐ read it three times
backend/apps/common/permissions.py       ⭐
backend/apps/tasks/models.py
backend/apps/tasks/serializers.py        ⭐ the validate() method
backend/apps/tasks/views.py              ← notice how short it is
backend/apps/tasks/filters.py
```

**Concepts**
- Abstract base models, `related_name="+"` and `%(class)ss`
- How `get_queryset()` produces 404-not-403
- Why `has_object_permission` alone does not protect lists
- Derived fields: `workspace` from the parent

**Answer these**
1. Why is `apps/tasks/views.py` only 25 lines? Where is the rest?
2. What exactly protects a create, given `get_queryset` does not run?
3. What breaks if `workspace` were writable on `TaskSerializer`?
4. Why is `.distinct()` needed on the scoped queryset?
5. Why do the permission classes import `Workspace` inside functions?

**Done when:** you can list the four things `WorkspaceScopedViewSet` gives every
subclass.

---

## Stage 5 — The Database

**Time:** 90 minutes

**Read**
1. [09-database-architecture.md](09-database-architecture.md)
2. [10-database-tables.md](10-database-tables.md)
3. [database/relationships.md](database/relationships.md)
4. [database/queries.md](database/queries.md)

**Do this** with the app running:
```sql
\dt
\d tasks_task
\d knowledge_documentchunk
SELECT action, COUNT(*) FROM activities_activity GROUP BY action;
```

**Concepts**
- UUID primary keys: benefits and costs
- `on_delete` as encoded business decisions
- Generic foreign keys and what they give up
- pgvector, HNSW, and why the opclass must match the query
- Deliberate denormalisation and its stated reasons

**Answer these**
1. Which two foreign keys would you change, and why?
2. Why is `workspace_id` duplicated onto `DocumentChunk`?
3. Why are workspace slugs global but project slugs per-workspace?
4. What does the database *not* enforce? Where is it enforced instead?
5. Where are the N+1s?

**Done when:** you can draw the eight-table spine and name every `on_delete`
choice on the user table.

---

## Stage 6 — Authentication

**Time:** 90 minutes

**Read**
1. [08-authentication-authorization.md](08-authentication-authorization.md) — all of it
2. [api/authentication.md](api/authentication.md)

**Open**
```
backend/apps/accounts/models.py
backend/apps/accounts/serializers.py     ← EmailTokenObtainPairSerializer, the reset serializer
backend/apps/accounts/views.py           ⭐ especially _blacklist_all_refresh_tokens
backend/apps/common/throttling.py        ← read the comments
backend/apps/common/channels_auth.py
backend/config/settings/base.py          ← the SIMPLE_JWT block
frontend/src/components/auth/login-form.tsx
```

**Do this:** log in with DevTools open. Watch the cookies appear. Delete the
access cookie and make a request — watch the refresh fire.

**Concepts**
- Rotation + blacklist making a refresh token single-use
- Why reset tokens self-invalidate (derived from the password hash and last_login)
- IP-keyed versus user-keyed throttling
- The three-layer guard, and which one is real

**Answer these**
1. Why does the login response include the user object?
2. What exactly happens on `POST /auth/password-reset/confirm/`? All of it.
3. Why does password reset revoke every session?
4. Why does the reset endpoint always return 202?
5. Why is the websocket token in the query string, and what mitigates it?

**Done when:** you can narrate login → token expiry → silent refresh → logout
without notes.

---

## Stage 7 — Business Logic

**Time:** 2 hours

**Read**
1. [13-business-logic.md](13-business-logic.md)
2. [modules/handovers.md](modules/handovers.md) ⭐
3. [modules/collaboration.md](modules/collaboration.md)
4. [modules/activity-audit.md](modules/activity-audit.md)

**Open**
```
backend/apps/handovers/serializers.py    ⭐
backend/apps/handovers/views.py          ⭐ the review action
backend/apps/mentions/services.py        ⭐ sync_comment_mentions
backend/apps/notifications/services.py
backend/apps/notifications/handlers.py
backend/apps/activities/handlers.py      ⭐
backend/apps/activities/services.py      ⭐ the suppression guard
```

**Concepts**
- Signals as decoupling, and the `queryset.update()` blind spot
- `weak=False` and `dispatch_uid`
- Idempotent reconciliation (the mention sync)
- `transaction.on_commit` for ordering with external systems

**Answer these**
1. List every rule enforced during handover review.
2. Why does approval write to another app's table?
3. Why doesn't editing a comment re-notify everyone mentioned?
4. Explain the workspace-deletion suppression guard and the bug it fixes.
5. Which writes does the audit log miss?

**Done when:** you can tell the `_workspaces_being_deleted` story as a debugging
narrative.

---

## Stage 8 — The AI Pipeline

**Time:** 2 hours

**Read**
1. [modules/documents-knowledge.md](modules/documents-knowledge.md)
2. [modules/ai-assistant.md](modules/ai-assistant.md)
3. [14-algorithms.md](14-algorithms.md) — sections 1–5

**Open**
```
backend/apps/knowledge/handlers.py
backend/apps/knowledge/services/processor.py    ⭐
backend/apps/knowledge/services/chunker.py
backend/apps/knowledge/services/extractor.py
backend/apps/knowledge/services/search.py       ⭐
backend/apps/knowledge/models.py                ← the HnswIndex
backend/apps/ai/services/rag.py                 ⭐
backend/apps/ai/services/security.py            ⭐
backend/apps/ai/services/prompts.py
backend/apps/ai/services/action_items.py
backend/apps/ai/providers/factory.py
```

**Do this:** upload a `.txt` file, then
```sql
SELECT chunk_index, LEFT(content, 60) FROM knowledge_documentchunk
WHERE document_id = '<id>' ORDER BY chunk_index;
```
Then search for a phrase from it at `/ai/search`.

**Concepts**
- Chunk overlap and why boundaries matter
- Cosine distance, normalised vectors, and score = 1 − distance
- HNSW versus IVFFlat
- The three trust levels in a RAG prompt
- Treating LLM output as untrusted input

**Answer these**
1. Trace an upload all the way to a searchable vector.
2. Why is the workspace filter *before* the vector ordering?
3. What breaks if you switch to a 1536-dimension provider?
4. How does `_parse` defend against a model that returns prose around its JSON?
5. Why aren't AI-generated tasks saved automatically?

**Done when:** you can draw both halves of the AI diagram and explain the
guardrails honestly, including their limits.

---

## Stage 9 — Operations & Debugging

**Time:** 90 minutes

**Read**
1. [17-error-handling.md](17-error-handling.md)
2. [18-security.md](18-security.md) ⭐
3. [19-performance-scalability.md](19-performance-scalability.md)
4. [23-troubleshooting.md](23-troubleshooting.md)
5. [25-known-limitations.md](25-known-limitations.md) ⭐

**Do this**
- Break something deliberately: stop PostgreSQL and hit `/api/v1/health/`.
- Open React Query Devtools and watch a key go stale.
- Count queries: `CaptureQueriesContext` around `GET /documents/`.

**Concepts**
- Which failures are swallowed, and why each one is defensible
- N+1 detection and the `annotate`/`Prefetch` fix
- Why there is no connection pooling and what that costs

**Answer these**
1. What are the three biggest security gaps, and their fixes?
2. Where are the N+1s and how much do they cost?
3. What breaks first under load?
4. Which six errors are deliberately swallowed, and why is each right?
5. What is missing before this could go to production?

**Done when:** you can list your own five worst weaknesses with a fix for each,
unprompted.

---

## Stage 10 — Interview Preparation

**Time:** 2–3 hours, spread out

**Read, in order**
1. [interviews/project-explanation.md](interviews/project-explanation.md) — practise the 3-minute version out loud
2. [interviews/whiteboard.md](interviews/whiteboard.md) — draw it three times
3. [interviews/beginner-questions.md](interviews/beginner-questions.md)
4. [interviews/intermediate-questions.md](interviews/intermediate-questions.md)
5. [interviews/advanced-questions.md](interviews/advanced-questions.md)
6. [interviews/difficult-followups.md](interviews/difficult-followups.md) ⭐
7. [interviews/code-walkthrough.md](interviews/code-walkthrough.md)
8. [interviews/memorize.md](interviews/memorize.md) — last

**Practise out loud**
- The 30-second version, word for word
- The 3-minute version, twice, timed
- Drawing the architecture while narrating
- Chain 1 (JWT) and Chain 2 (multi-tenancy) from
  [difficult-followups.md](interviews/difficult-followups.md)

**Done when:** you can be asked any of the ten questions in
[interviews/README.md](interviews/README.md#the-10-questions-most-likely-to-be-asked)
and answer for two minutes without hesitating.

---

## Self-assessment

Score yourself honestly. Anything below 4 means go back to that stage.

| # | Can you… | Stage | 1–5 |
|---|---|---|---|
| 1 | Draw the architecture from memory | 1 | |
| 2 | Name every layer between click and SQL | 1, 4 | |
| 3 | Explain the startup sequence and the three round trips | 2 | |
| 4 | Explain the workspace-provider race fix | 2 | |
| 5 | Write the single-flight refresh on a whiteboard | 3 | |
| 6 | Explain what `WorkspaceScopedViewSet` gives you | 4 | |
| 7 | Explain why cross-tenant reads return 404 | 4 | |
| 8 | Draw the eight-table spine | 5 | |
| 9 | Justify every `on_delete` on the user table | 5 | |
| 10 | Narrate login → expiry → refresh → logout | 6 | |
| 11 | List every handover review rule | 7 | |
| 12 | Tell the suppression-guard debugging story | 7 | |
| 13 | Trace an upload to a searchable vector | 8 | |
| 14 | Explain the RAG guardrails **and their limits** | 8 | |
| 15 | List your five worst weaknesses with fixes | 9 | |
| 16 | Give the 3-minute pitch fluently | 10 | |

**Below 60/80** — do stages 1, 4 and 6 again.
**60–70** — focus on stages 7–9; you know the mechanics but not the judgement.
**Above 70** — you are ready. Practise out loud.

---

## The shortcut

If you have **one evening**:

1. [project-cheat-sheet.md](project-cheat-sheet.md) — 10 min
2. [02-system-architecture.md](02-system-architecture.md) — 20 min
3. `apps/common/viewsets.py` + `apps/common/permissions.py` — 15 min
4. [08-authentication-authorization.md](08-authentication-authorization.md) — 30 min
5. `frontend/src/lib/api/client.ts` — 15 min
6. [modules/handovers.md](modules/handovers.md) — 20 min
7. [interviews/project-explanation.md](interviews/project-explanation.md) — practise aloud, 30 min
8. [25-known-limitations.md](25-known-limitations.md) — 15 min

**~2.5 hours for roughly 70% of the value.** The rest is depth.
