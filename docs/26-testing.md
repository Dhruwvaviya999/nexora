# 26 — Testing

[← Back to index](README.md)

---

## 1. What exists

### Backend — Django test runner

No pytest. `manage.py test` selects `config.settings.test` automatically.

| File | `def test_` methods | Covers |
|---|---|---|
| `apps/accounts/tests.py` | 32 | Password reset (reuse, tampering, enumeration, session revocation), credential rate limits, **and the httpOnly refresh-cookie contract** |
| `apps/common/tests.py` | **21** ⭐ new | **Tenant isolation**, the role matrix, and the scheduled maintenance tasks |
| `apps/comments/tests.py` | **18** ⭐ new | Target whitelist, reply inheritance, soft delete, author-vs-admin permissions |
| `apps/documents/tests.py` | **17** ⭐ new | Upload metadata, size/type validation, and the authenticated download endpoint as a tenant boundary |
| `apps/handovers/tests.py` | 16 | The review workflow |
| `apps/workspaces/tests.py` | 15 | The role matrix — who may administer, transfer and delete |
| `apps/tasks/tests.py` | **15** ⭐ new | Workspace derivation, member validation, filters |
| `apps/mentions/tests.py` | **13** ⭐ new | Token parsing and idempotent sync |
| `apps/projects/tests.py` | **12** ⭐ new | Archive/restore, per-workspace slug uniqueness |
| `apps/notifications/tests.py` | 12 | WebSocket auth, per-user isolation, realtime push |
| `apps/invitations/tests.py` | 9 | Email delivery and the accept/reject lifecycle |
| `apps/knowledge/tests.py` | 8 | Embedding scheduling, retries, failure recording |
| `apps/core/tests_seed_demo.py` | 5 | The demo seeder |
| `apps/core/tests.py` | 4 | Health and core endpoints |
| `apps/activities/tests.py` | 3 | The audit trail, including cascade deletes |
| `apps/core/tests_smoke.py` | 1 | End-to-end walk across every API area |
| **Total** | **201** | up from 93 |

**No empty test files remain.** All six that were 0 lines now have coverage.

### Frontend — Vitest + Testing Library

Seven test files, 45 tests:

```
components/auth/forgot-password-form.test.tsx
components/shared/search-input.test.tsx
lib/auth/token-storage.test.ts      ⭐ new — the token-storage security contract
lib/format.test.ts
lib/realtime.test.ts
lib/utils.test.ts
providers/workspace-provider.test.tsx
```

### CI

`.github/workflows/ci.yml` runs the backend suite against real
`pgvector/pgvector:pg16` and `redis:7-alpine`, plus `pnpm typecheck`, `pnpm
lint`, `pnpm test` and `pnpm build` on the frontend. Also
`manage.py check --fail-level WARNING` and `makemigrations --check --dry-run`.

**No coverage threshold is enforced** in either suite.

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

| Area | Tests | Why it was the right place to spend effort |
|---|---|---|
| **Tenant isolation** ⭐ | 21 (`common`) | One base class carries the whole multi-tenant guarantee; a regression leaks every endpoint at once |
| Auth + password reset | 32 (`accounts`) | Reuse, tampering, enumeration, session revocation — and now the httpOnly cookie contract |
| Comments | 18 | Whitelist, reply inheritance, soft delete, the author-vs-admin split |
| Documents | 17 | Upload validation, and the download endpoint treated as a tenant boundary |
| Handover workflow | 16 | The densest business logic in the project |
| Role matrix | 15 (`workspaces`) + 5 (`common`) | Permission bugs are silent and severe |
| Task serializer | 15 | Workspace derivation and membership validation — the correctness core |
| Mention sync | 13 | Idempotency: editing a comment must not re-notify |
| WebSocket isolation | 12 | User A's socket must never receive user B's notification |

### The smoke test

`apps/core/tests_smoke.py` walks every API area, checks tenancy isolation and
anonymous access in one method. It remains the safety net for anything without
dedicated coverage.

---

## 4. What is not tested

### Backend gaps, ranked by risk

| Gap | Why it matters |
|---|---|
| **The AI layer** | `apps/ai` still has **no test file**. No coverage of `resolve_workspace`, prompt building, `_parse` in `action_items`, or the confidence thresholds. **Now the largest untested surface in the backend.** |
| **Dashboard and analytics maths** | The overdue definition, the weekly buckets, `avg_review_hours`. Aggregation bugs are easy to introduce and invisible |
| **Query counts** | Nothing uses `assertNumQueries`, so the known N+1s can silently get worse |
| **Handover concurrency** | Two managers approving simultaneously is a known check-then-act race with no test |

### Frontend gaps

| Gap | Why it matters |
|---|---|
| `lib/api/client.ts` | The single-flight refresh, one-shot retry and error normalisation are still **untested** — the most logic-dense file in the frontend |
| `providers/auth-provider.tsx` | Bootstrap-from-cookie, login, logout cache clearing |
| `use-notification-socket.ts` | Backoff, close-code handling, reconnection |
| Any page component | Zero page-level tests |

`lib/auth/token-storage.test.ts` now covers the storage security contract, and
`providers/workspace-provider.test.tsx` the three-source resolution. The client
remains the gap that matters most.

---

## 5. The tests that should exist next

1. **`lib/api/client.test.ts`** — highest value by a wide margin. Ten concurrent
   401s must trigger exactly **one** refresh; one retry only; `skipAuth` never
   refreshes; FormData gets no `Content-Type`; a non-2xx becomes an `ApiError`
   with `details` preserved.
2. **`apps/ai/tests.py`** — `resolve_workspace` denies non-members; retrieval
   never returns another workspace's chunks; `_parse` survives prose-wrapped
   JSON, invalid priorities and malformed dates.
3. **`assertNumQueries`** around `GET /documents/` and `GET /dashboard/`, so the
   N+1 fixes cannot regress once made.
4. **`apps/core/tests.py`** — a completed task with a past due date is *not*
   overdue; the 8-week window includes empty weeks.
5. **Handover concurrency** — two approvals racing; document the intended
   behaviour, then implement it.

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

**It tests the risky parts first.** Auth, tenancy, roles, the handover workflow
and websocket isolation carry the most coverage; plain CRUD leans on the smoke
test. That allocation is now backed by dedicated files rather than relying on
the smoke test alone.

**The test settings are engineered, not copy-pasted.** Every override in
`test.py` solves a specific problem and carries a comment. The throttle-rate
insight — a rate of `None`, not just clearing the classes — is the kind of
detail people usually find the hard way.

**The new tests found a real bug.** `apps/documents/tests.py` immediately failed
on `test_title_defaults_to_the_filename`: `Document.title` has no `blank=True`,
so DRF inferred `required=True` and the filename fallback in `create()` was
unreachable. Any upload without an explicit title had been returning 400 — and
the frontend only sends one when the user types it. That is the argument for
writing the tests, made concretely.

**Remaining honest weakness:** the frontend's most logic-dense file
(`lib/api/client.ts`) still has no test, and `apps/ai` has none at all. Those
are the next two to write.
