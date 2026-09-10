# 26 — Testing

[← Back to index](README.md)

---

## 1. What exists

### Backend — Django test runner

No pytest. `manage.py test` selects `config.settings.test` automatically.

| File | `def test_` methods | Covers |
|---|---|---|
| `apps/accounts/tests.py` | 20 | Password reset (reuse, tampering, enumeration, session revocation) and credential rate limits |
| `apps/handovers/tests.py` | 16 | The review workflow |
| `apps/workspaces/tests.py` | 15 | The role matrix — who may administer, transfer and delete |
| `apps/notifications/tests.py` | 12 | WebSocket auth, per-user isolation, realtime push |
| `apps/invitations/tests.py` | 9 | Email delivery and the accept/reject lifecycle |
| `apps/knowledge/tests.py` | 8 | Embedding scheduling, retries, failure recording |
| `apps/core/tests_seed_demo.py` | 5 | The demo seeder: idempotency, determinism, scoped reset |
| `apps/core/tests.py` | 4 | Health and core endpoints |
| `apps/activities/tests.py` | 3 | The audit trail, including cascade deletes |
| `apps/core/tests_smoke.py` | 1 | An end-to-end walk across **every** API area, tenancy isolation, anonymous access |
| **Total** | **93** | |

> The root `README.md` says "89 tests". The `grep -c "def test_"` count is 93.
> The suite was not executed while writing this documentation, so which number
> the runner reports is **not confirmed**. The discrepancy is small and does not
> change the picture.

**Empty files (0 lines each):** `apps/comments/tests.py`,
`apps/documents/tests.py`, `apps/mentions/tests.py`, `apps/projects/tests.py`,
`apps/tasks/tests.py`, `apps/common/tests.py`.

### Frontend — Vitest + Testing Library

Six test files:

```
components/auth/forgot-password-form.test.tsx
components/shared/search-input.test.tsx
lib/format.test.ts
lib/realtime.test.ts
lib/utils.test.ts
providers/workspace-provider.test.tsx
```

Config: `vitest.config.mts` + `vitest.setup.ts`, jsdom environment,
`@testing-library/jest-dom` matchers. Scripts: `pnpm test`, `test:watch`,
`test:coverage`.

### CI

`.github/workflows/ci.yml` runs the backend suite against real
`pgvector/pgvector:pg16` and `redis:7-alpine`, plus `pnpm typecheck`, `pnpm
lint`, `pnpm test` and `pnpm build` on the frontend. Also
`manage.py check --fail-level WARNING` and
`makemigrations --check --dry-run`.

**No coverage threshold is enforced** in either suite.

---

## 2. What makes the test settings work

`config/settings/test.py` is worth reading in full — it is short and every line
solves a real problem.

| Setting | Reason (from the file's own comments) |
|---|---|
| `EMAIL_BACKEND = locmem` | Mail collects in `django.core.mail.outbox` so tests can assert on it |
| `CELERY_TASK_ALWAYS_EAGER = True` + `EAGER_PROPAGATES = True` | Tasks run inline **and re-raise**, so a broken task fails its test |
| `CHANNEL_LAYERS = InMemory` | WebSocket tests need no Redis |
| `CACHES = locmem` | No Redis |
| **All throttle rates `None`** | *"a test that walks 40 endpoints is not an attack."* Clearing `DEFAULT_THROTTLE_CLASSES` alone is not enough, because the auth views name their throttles explicitly — a rate of `None` is what actually disables a scope |
| `PASSWORD_HASHERS = [MD5]` | *"The default PBKDF2 hasher is deliberately slow; the suite creates a lot of users and does not test hashing strength"* |
| `CORS_ALLOWED_ORIGINS` pinned | `config/asgi.py` hands the list to the websocket `OriginValidator` **at import time**, so `override_settings` could not change it later — the consumer tests connect with exactly this origin |

`apps/accounts/tests.py` patches the throttle rates back in for the tests that
specifically exercise rate limiting — noted in the `test.py` comment.

---

## 3. What is well tested

The four best-covered areas, and why they were the right choices:

### Authentication and password reset (20 tests)

The README lists the specific scenarios: **reuse, tampering, enumeration, session
revocation**. Those are exactly the four things that go wrong with password
reset, and all four are subtle. Testing that a reset link stops working after use
and that every refresh token is blacklisted is high-value coverage.

### The role matrix (15 tests)

"Who may administer, transfer and delete." Permission bugs are silent and severe;
a matrix test is the right shape for them.

### The handover workflow (16 tests)

The densest business logic in the project — reviewer roles, single review,
mandatory rejection comment, task reassignment on approval. Correctly the
most-tested module.

### WebSocket auth and isolation (12 tests)

Testing that user A's socket never receives user B's notification is real
security coverage, and websocket tests are non-trivial to write.

### The smoke test

`apps/core/tests_smoke.py` is one test method that walks every API area, checks
tenancy isolation and checks anonymous access. It is the safety net that gives
`projects` and `tasks` *some* coverage despite their empty test files.

---

## 4. What is not tested

### Backend gaps, ranked by risk

| Gap | Why it matters |
|---|---|
| **Task serializer validation** | `workspace` derivation from project, non-member assignee rejection, reporter defaulting. Core correctness with **no direct test** |
| **Mention parsing and sync** | The `@[Name](uuid)` regex and the idempotent add/remove logic. Subtle, and `apps/mentions/tests.py` is empty |
| **Comment permissions** | Author-edit / author-or-admin-delete, soft delete, reply-to-deleted rejection. `apps/comments/tests.py` is empty |
| **Document upload path** | Multipart handling, `file_size`/`file_type` capture, default title. `apps/documents/tests.py` is empty |
| **Project archive/restore** | Small, but `apps/projects/tests.py` is empty |
| **Dashboard and analytics maths** | The overdue definition, the weekly buckets, `avg_review_hours`. Aggregation bugs are easy to introduce and invisible |
| **The AI layer** | No test file for `apps/ai` at all — no coverage of `resolve_workspace`, prompt building, `_parse` in `action_items`, or the confidence thresholds |
| **Filtering and pagination** | No test asserts that `?status=` or `?due_before=` actually filters |
| **`WorkspaceScopedViewSet` itself** | The single most security-critical class in the backend, and `apps/common/tests.py` is empty. It is exercised indirectly by the smoke test |

### Frontend gaps

| Gap | Why it matters |
|---|---|
| `lib/api/client.ts` | The refresh mechanism, single-flight behaviour and error normalisation are **completely untested** — and this is the most logic-dense file in the frontend |
| `providers/auth-provider.tsx` | Bootstrap, login, logout cache clearing |
| `use-notification-socket.ts` | Backoff, close-code handling, reconnection |
| Any page component | Zero page-level tests |
| Any mutation hook | Zero |

`lib/realtime.test.ts` covers the URL derivation, and
`providers/workspace-provider.test.tsx` covers the three-source resolution — both
good choices. But the client is the gap that matters most.

---

## 5. The tests that should exist next

Ranked by value-per-effort. These are derived from the actual risk surface.

### Backend — top 10

1. **`apps/common/tests.py` — tenancy**
   - A member of workspace A gets **404** for a task in workspace B.
   - `perform_create` rejects a workspace you are not in.
   - `created_by`/`updated_by` are stamped correctly.
   *This is the single highest-value missing test in the project.*

2. **`apps/tasks/tests.py` — serializer rules**
   - `workspace` is derived from the project and cannot be client-supplied.
   - A non-member `assignee_id` is rejected with a field error.
   - `reporter` defaults to the requesting user.

3. **`apps/mentions/tests.py` — sync idempotency**
   - Editing a comment twice does not create duplicate mentions or re-notify.
   - Removing a mention from the text deletes the row.
   - A non-member mention is ignored.
   - Self-mention creates no notification.

4. **`apps/comments/tests.py` — permissions and soft delete**
   - Another user cannot edit my comment; an admin can delete it.
   - Delete blanks the content and renders `[deleted]`.
   - Replying to a deleted comment is rejected.

5. **`apps/core/tests.py` — dashboard maths**
   - A completed task with a past due date is **not** overdue.
   - `active_projects` excludes archived ones.
   - The 8-week window includes empty weeks.

6. **`apps/handovers/tests.py` — the missing case**
   - Two pending handovers on one task. *Currently allowed — write the test that
     documents the intended behaviour, then implement it.*

7. **`apps/ai/tests.py` — isolation and parsing**
   - `resolve_workspace` denies a non-member.
   - Retrieval never returns another workspace's chunks.
   - `action_items._parse` handles prose-wrapped JSON, invalid priorities and
     malformed dates.

8. **`apps/documents/tests.py` — upload**
   - Multipart upload captures `file_size` and `file_type`.
   - Title defaults to the filename.
   - An unsupported extension creates **no** `EmbeddingJob`.

9. **Filtering** — one test per FilterSet asserting the query param actually
   narrows results, including `due_before`/`due_after` and the handover `project`
   filter.

10. **`apps/projects/tests.py`** — archive/restore, and per-workspace slug
    uniqueness.

### Frontend — top 5

1. **`lib/api/client.test.ts`** — the highest-value frontend test by a wide
   margin:
   - A 401 triggers exactly one refresh and one retry.
   - Ten concurrent 401s trigger exactly **one** refresh (single-flight).
   - A failed refresh clears tokens and rethrows.
   - `skipAuth` requests never refresh.
   - FormData bodies get **no** `Content-Type` header.
   - A non-2xx becomes an `ApiError` with `details` preserved.

2. **`providers/auth-provider.test.tsx`** — bootstrap with and without cookies;
   `logout()` calls `queryClient.clear()`.

3. **`hooks/use-notification-socket.test.ts`** — close code 4401 backs off to the
   slowest interval; 1000 does not reconnect; malformed JSON is ignored.

4. **`lib/api/errors.test.ts`** — `applyFieldErrors` maps a DRF
   `{field: [msg]}` body onto `setError`.

5. **One page integration test** — the handover detail page: the review card
   renders for a manager and not for a member.

---

## 6. How to run everything

```bash
# Backend
cd backend
python manage.py test                       # all 93
python manage.py test apps.handovers        # one app
python manage.py test apps.accounts.tests.PasswordResetTests -v 2
python manage.py test --parallel            # faster on multi-core

# Frontend
cd frontend
pnpm test                                   # vitest run
pnpm test:watch
pnpm test:coverage
pnpm typecheck
pnpm lint

# What CI runs, in order
python manage.py check --fail-level WARNING
python manage.py makemigrations --check --dry-run
python manage.py test --verbosity 2
pnpm install --frozen-lockfile && pnpm typecheck && pnpm lint && pnpm test && pnpm build
```

---

## 7. Testing philosophy visible in the code

Three things this suite does well, worth articulating:

**It tests the risky parts, not everything equally.** Auth, roles, the handover
workflow and websocket isolation are covered heavily; plain CRUD is left to the
smoke test. That is a defensible allocation of effort — though it has gone too
far, since `tasks` and `projects` have *no* dedicated file at all.

**The test settings are engineered, not copy-pasted.** Every override in
`test.py` solves a specific problem, and each carries a comment explaining it.
The throttle-rate insight (`None`, not just clearing the classes) is the kind of
detail people usually discover the hard way.

**One broad smoke test as a safety net.** `tests_smoke.py` walking every API area
means an accidental breakage in an untested app still fails CI.

**And one honest weakness:** the frontend's most logic-dense file
(`lib/api/client.ts`) has no test at all, while the four files that *are* tested
are among the simplest. That is worth fixing before it is worth adding any more
page tests.

---

**Next:** [modules/](modules/) · [api/](api/README.md) ·
[interviews/](interviews/README.md)
