# Interview — What You Must Know Cold

[← Interviews index](README.md)

The morning-of file. Everything here is a fact you should not have to look up.

---

## 1. The stack, in one breath

**Next.js 16 (App Router) + React 19 + TypeScript + Tailwind 4 + shadcn/ui +
TanStack Query** on the front.
**Django 5.1 + DRF + SimpleJWT + Channels + Celery** on the back.
**PostgreSQL 16 + pgvector**. **Redis** for broker, channel layer and throttle
cache. **Docker compose**, **GitHub Actions**.

**No Axios** — a hand-written `fetch` wrapper.
**No Redux** — TanStack Query plus two React Contexts.
**No raw SQL** — Django ORM everywhere.

---

## 2. The one-sentence architecture

> Every object belongs to a workspace, and `WorkspaceScopedViewSet.get_queryset()`
> enforces that on every query — so tenant isolation is structural, not something
> each endpoint has to remember.

---

## 3. The eight modules

Workspaces & membership · Projects & tasks · **Handovers** · Documents &
knowledge · **AI assistant** · Collaboration (comments/mentions/notifications) ·
Activity & audit · Dashboard & analytics.

---

## 4. The numbers

| Thing | Number |
|---|---|
| Application tables | 19 |
| Frontend pages (`page.tsx`) | 37 |
| Django apps | 15 |
| API route groups under `/api/v1/` | 13 |
| TanStack Query hooks | 16 |
| Backend test methods | **201** |
| Frontend test files | 7 (45 tests) |
| Access token lifetime | **15 minutes** |
| Refresh token lifetime | **7 days** |
| Page size | **20** |
| Embedding dimensions | **384** |
| Chunk size / overlap | **220 / 40 words** |
| Retrieval top-K | **6** |
| Max cosine distance | **0.75** |
| Chat history turns | **10** |
| AI rate limit | **30/hour per user** |
| Login rate limit | **10/min per IP** |
| CSV export cap | **10,000 rows** |

---

## 5. The four roles

**Owner** — everything, plus transfer ownership and delete the workspace.
**Admin** — manage members and invitations, edit the workspace, moderate
comments, review handovers, change AI settings.
**Manager** — member, **plus handover review**. That is the *only* thing that
distinguishes a manager.
**Member** — create and edit content, submit handovers, comment, use AI.

`REVIEWER_ROLES = (OWNER, ADMIN, MANAGER)`

---

## 6. The 12 files that matter most

| File | Why |
|---|---|
| `backend/apps/common/viewsets.py` | Tenant isolation for the whole system |
| `backend/apps/common/permissions.py` | The five role classes |
| `backend/apps/common/models.py` | The four abstract bases |
| `backend/apps/handovers/views.py` | The richest business logic |
| `backend/apps/ai/services/rag.py` | The RAG orchestration |
| `backend/apps/knowledge/services/search.py` | The vector query |
| `backend/apps/activities/handlers.py` | Signal-driven auditing |
| `backend/config/settings/base.py` | Every configuration decision |
| `backend/config/asgi.py` | HTTP/WebSocket protocol split |
| `frontend/src/lib/api/client.ts` | JWT, single-flight refresh, errors |
| `frontend/src/providers/auth-provider.tsx` | Session state |
| `frontend/src/providers/workspace-provider.tsx` | The active tenant |

---

## 7. Auth flow — seven beats

1. `POST /auth/login/` → body `{access, user}`. The user object is why the custom
   serializer exists — it saves a `/auth/me/` round trip.
2. The **refresh token is stripped from the body** into an **httpOnly** cookie
   (`nexora_refresh`, path `/api/v1/auth/`). Script can never read it.
3. The **access token lives in memory only** — a module variable, gone on reload.
4. Every request carries `Authorization: Bearer <access>` + `credentials:"include"`.
5. On a 401, **single-flight refresh** with an *empty body* — the browser
   attaches the cookie. Rotation writes the new refresh back to the cookie.
6. `src/proxy.ts` reads `nexora.session`, a marker containing `"1"` and **no
   secret** — it runs on the frontend origin and cannot see the API origin's
   cookie. All twelve protected route trees are matched.
7. Logout blacklists from the cookie, clears it on every path, and calls
   `queryClient.clear()`.

---

## 8. The handover rules

Cannot hand to yourself · recipient must be a member · only the submitter edits ·
only while pending · the task can never be swapped · only owner/admin/manager
reviews · reviewed **once** · **rejection requires a comment** · approval sets
`task.assignee` · both outcomes notify · exportable as PDF.

**The gap:** nothing prevents two pending handovers on the same task.

---

## 9. The RAG pipeline

```
upload → post_save signal → EmbeddingJob → Celery (on_commit)
       → extract (pypdf / python-docx) → chunk (220/40)
       → embed (all-MiniLM-L6-v2, 384-dim, normalised)
       → bulk_create with HNSW cosine index

question → sanitize → embed → cosine kNN WITHIN THE WORKSPACE (top 6, ≤0.75)
        → + structured context (8 projects, task counts, 10 keyword-matched tasks)
        → fenced as untrusted + guardrails → LLM → {answer, sources, confidence}
```

Confidence: `≥0.6` high · `≥0.4` or structured present medium · else low.

**AI-generated tasks are never persisted** — returned for review, then created
through the normal Task API.

---

## 10. Signals — what they do

| App | Trigger | Effect |
|---|---|---|
| `activities` | `post_save`/`post_delete` on 7 models | Audit row |
| `mentions` | `post_save` on Comment | Re-sync `Mention` rows, emit `user_mentioned` |
| `notifications` | `user_mentioned`, and Comment replies | `create_notification()` |
| `knowledge` | `post_save` on Document, **created only** | Queue embedding |

**No domain app imports `activities`.** That is the decoupling.

**The blind spot:** `queryset.update()`, `bulk_create` and raw SQL fire no
signals, so those writes are unaudited.

---

## 11. Degradation table — say this one out loud

| Down | Behaviour |
|---|---|
| Redis (broker) | Tasks run inline |
| Redis (channels) | Polling every 30s |
| Redis (cache) | Per-process throttle counters |
| SMTP | Logged, retried 3× by Celery |
| LLM provider | 502 with the provider's message |
| pgvector | Clean 503 with setup instructions |
| **PostgreSQL** | The only hard dependency |

Local development needs **nothing but PostgreSQL**.

---

## 12. Recently fixed — lead with these

1. **httpOnly refresh cookie** — access token memory-only, edge guard reads a
   value-less marker. XSS exposure: 15 minutes, not 7 days.
2. **Authenticated document download** — the old `/media/` URL was an
   unauthenticated cross-tenant read *and* 404'd in production.
3. **Upload validation** — 25 MB cap, extension allow-list, forced attachment.
4. **Error boundaries** ×3 + `isError` on 8 pages.
5. **Celery beat** — 4 nightly pruning tasks; nothing ran before.
6. **Tests 93 → 201**, no empty files. They caught a real bug: uploads with no
   title always returned 400 (`Document.title` lacked `blank=True`).

## 12b. Still open

1. **No `CONN_MAX_AGE`** — new DB connection per request.
2. **Document list N+1** — 41 queries for 20 rows.
3. **No `completed_at`** — analytics approximates from `updated_at`.
4. **Two pending handovers per task** possible.
5. **No logging / error tracking** — the largest remaining gap.
6. **`apps/ai` has no tests**; `lib/api/client.ts` has none either.

---

## 13. Ten one-line answers

| Question | Answer |
|---|---|
| Why 404 not 403 across tenants? | The row was never in the queryset — so the API never confirms the id exists |
| Why cookies not localStorage? | So the Next.js edge proxy can read them server-side |
| Why single-flight refresh? | Refresh tokens rotate and are single-use — parallel refreshes would invalidate each other |
| Why is `workspace` read-only on Task? | It is derived from the project, so a client cannot mismatch them |
| Why signals for the audit log? | One line per model, and domain apps stay unaware of auditing |
| Why `on_commit` before queueing? | Otherwise the worker can read a row that is not visible yet, or one that rolled back |
| Why does the websocket carry no data? | It is a signal to refetch — one source of truth, no cache drift |
| Why pgvector and not Pinecone? | The tenant filter and the vector search are one query, one backup, one transaction |
| Why HNSW and not IVFFlat? | Documents arrive one at a time; IVFFlat needs re-training, HNSW is incremental |
| Why aren't AI tasks saved automatically? | The model never writes to the database — suggestions go through the same validation as manual tasks |

---

## 14. The three sentences to lead with

> "Tenant isolation is structural — one base class enforces it on every query,
> and cross-tenant reads return 404 rather than 403."

> "Everything degrades instead of failing. Postgres is the only hard dependency."

> "The AI writes nothing — retrieval is workspace-scoped, content is fenced as
> untrusted, and generated tasks go through the normal Task API for review."
