# 10 — Database Tables

[← Back to index](README.md) · [Architecture](09-database-architecture.md) ·
[Relationships](database/relationships.md)

Every column below was read from the model definition. Types are the Django field
type with the PostgreSQL type in brackets where it differs meaningfully.

Columns inherited from the abstract bases are listed once here and then referred
to as **[base]**:

| Inherited column | Type | From |
|---|---|---|
| `id` | UUID, PK, default `uuid4` | `UUIDModel` |
| `created_at` | timestamptz, auto_now_add | `TimeStampedModel` |
| `updated_at` | timestamptz, auto_now | `TimeStampedModel` |
| `created_by_id` | UUID FK → user, null, `SET_NULL` | `AuditModel` |
| `updated_by_id` | UUID FK → user, null, `SET_NULL` | `AuditModel` |
| `workspace_id` | UUID FK → workspace, `CASCADE` | `WorkspaceScopedModel` |

---

## 1. `accounts_user`

`backend/apps/accounts/models.py:46`

| Column | Type | Null | Key | Default | Purpose |
|---|---|---|---|---|---|
| `id` | UUID | no | PK | `uuid4` | Identity, exposed in APIs |
| `email` | varchar(254) | no | **unique** | — | **Login identifier** (`USERNAME_FIELD`) |
| `password` | varchar(128) | no | — | — | PBKDF2 hash, never the raw value |
| `name` | varchar(150) | no | — | `""` | Display name |
| `avatar` | varchar(200) URL | no | — | `""` | Avatar **URL** — no upload path exists |
| `is_active` | bool | no | — | `True` | Password reset only targets active users |
| `is_staff` | bool | no | — | `False` | Django admin access |
| `is_superuser` | bool | no | — | `False` | Django admin |
| `first_name`, `last_name` | varchar(150) | no | — | `""` | Inherited from `AbstractUser`, **unused** — `name` is used instead |
| `date_joined` | timestamptz | no | — | now | Default ordering is `-date_joined` |
| `last_login` | timestamptz | yes | — | null | Written on each token issue (`UPDATE_LAST_LOGIN`) |
| `created_at`, `updated_at` | timestamptz | no | — | auto | Declared on the model itself |

**Written by:** `RegisterSerializer.create` → `UserManager.create_user`;
`ProfileUpdateSerializer` (name, avatar only); `PasswordResetConfirmSerializer.save`;
SimpleJWT's `UPDATE_LAST_LOGIN`; `manage.py createsuperuser`; `seed_demo`.
**Read by:** every serializer that nests `UserSerializer`, `JWTAuthentication` on
every request, permission lookups.
**APIs:** `/auth/register/`, `/auth/login/`, `/auth/me/`, `/auth/password-reset/*`;
appears nested in almost every other response.
**UI depends on it:** avatars, `nav-user`, assignee dropdowns, comment authors,
`/settings`.

**Risks.** `first_name`/`last_name` exist but nothing uses them — a future
developer may write to the wrong field. `avatar` is an unvalidated URL server-side
(only the frontend zod schema checks it is a URL), so it is rendered as an
`<img src>` from user input.

---

## 2. `workspaces_workspace`

`backend/apps/workspaces/models.py:28`

| Column | Type | Null | Key | Default | Purpose |
|---|---|---|---|---|---|
| **[base]** `id`, `created_at`, `updated_at` | | | | | `BaseModel` |
| `name` | varchar(120) | no | — | — | Display name |
| `slug` | varchar(140) | no | **unique** | derived | URL-friendly id; auto-generated |
| `description` | text | no | — | `""` | Free text |
| `owner_id` | UUID FK → user | no | idx | — | **`CASCADE`** — see risk |

`save()` generates the slug when blank, appending `-2`, `-3`… until unique
(`_generate_unique_slug`, lines 49-56).

**Written by:** `WorkspaceViewSet.perform_create` (atomic, also creates the owner
membership), `transfer_ownership`.
**Read by:** every scoped query, the workspace switcher, the dashboard.
**Risk:** `owner` is `CASCADE`. Deleting a user deletes every workspace they own
and, by cascade, all its content. There is no ownership-orphan path.
**Risk:** the slug is globally unique, so two different companies cannot both
have "operations". Acceptable, but a real multi-tenant naming constraint.

---

## 3. `workspaces_workspacemember`

`backend/apps/workspaces/models.py:59`

| Column | Type | Null | Key | Default | Purpose |
|---|---|---|---|---|---|
| **[base]** `id`, `created_at`, `updated_at` | | | | | |
| `workspace_id` | UUID FK | no | idx, unique-with | — | `related_name="members"` |
| `user_id` | UUID FK | no | idx, unique-with | — | `related_name="workspace_memberships"` |
| `role` | varchar(20) | no | — | `member` | `owner` / `admin` / `manager` / `member` |
| `joined_at` | timestamptz | no | — | auto_now_add | Default ordering |

Unique constraint `unique_workspace_member` on `(workspace, user)`.

**This is the single most important table in the system.** Every permission check
and every tenant-scoping query reads it:

- `WorkspaceScopedViewSet.get_queryset()` → `filter(workspace__members__user=...)`
- `_membership()` in `apps/common/permissions.py`
- `resolve_workspace()` in `apps/ai/permissions.py`
- `_reviewer_membership()` in `apps/handovers/views.py`
- `_resolve_member()` in task and handover serializers

**Business rules:** the owner's membership cannot be edited through
`manage_member` — it raises "use transfer-ownership" (`views.py:104-107`).
Invitations may only grant `admin`/`manager`/`member`, never `owner`
(`INVITABLE_ROLES`, `invitations/models.py:37`).

---

## 4. `projects_project`

`backend/apps/projects/models.py:17`

| Column | Type | Null | Key | Default | Purpose |
|---|---|---|---|---|---|
| **[base]** all six | | | | | `WorkspaceScopedModel` |
| `name` | varchar(150) | no | — | — | |
| `slug` | varchar(170) | no | unique-with workspace | derived | Per-workspace unique |
| `description` | text | no | — | `""` | |
| `color` | varchar(7) | no | — | `#6366f1` | Hex accent used by the UI |
| `status` | varchar(20) | no | — | `planning` | `planning`/`active`/`on_hold`/`completed` |
| `archived` | bool | no | — | `False` | Soft hide; toggled by two actions |
| `owner_id` | UUID FK → user | yes | — | creator | `SET_NULL` |

`ProjectSerializer.create` defaults `owner` to the requesting user
(`serializers.py:41-46`).

**Written by:** `ProjectViewSet` (CRUD + `archive`/`restore`).
**Read by:** task/document filter dropdowns, project detail, dashboard,
`/search`, the RAG structured-context builder.
**Note:** `archived` and `status=completed` are independent. A project can be
completed but not archived, and vice versa; the dashboard counts them separately.
**Risk:** no index on `(workspace, status)` despite being filtered that way.

---

## 5. `tasks_task`

`backend/apps/tasks/models.py:24`

| Column | Type | Null | Key | Default | Purpose |
|---|---|---|---|---|---|
| **[base]** all six | | | | | |
| `project_id` | UUID FK | no | idx | — | `CASCADE`, `related_name="tasks"` |
| `title` | varchar(255) | no | — | — | |
| `description` | text | no | — | `""` | |
| `status` | varchar(20) | no | idx | `todo` | `todo`/`in_progress`/`review`/`completed`/`cancelled` |
| `priority` | varchar(20) | no | — | `medium` | `low`/`medium`/`high`/`critical` |
| `assignee_id` | UUID FK → user | yes | — | null | `SET_NULL` |
| `reporter_id` | UUID FK → user | yes | — | creator | `SET_NULL` |
| `due_date` | date | yes | — | null | Drives "overdue" |
| `start_date` | date | yes | — | null | Stored, **not used** by any view or filter |
| `estimated_hours` | numeric(6,2) | yes | — | null | Stored, **not used** by any view or filter |
| `labels` | jsonb | no | — | `[]` | String list; **not filterable** |

Indexes: `(workspace, status)`, `(project, status)`.

**Written by:** `TaskViewSet`, and `HandoverViewSet.review` on approval
(assignee + `updated_by` only).
**Read by:** task list/detail, project detail, dashboard stats, analytics
(status, priority, weekly, workload), RAG structured context, handover creation.

**Business rules:**
- `workspace` is **derived from the project** and is read-only
  (`serializers.py:76`).
- `assignee` and `reporter` must be workspace members (`_resolve_member`).
- `reporter` defaults to the creating user (`serializers.py:88-93`).
- "Open" means `todo`, `in_progress` or `review` — defined once as
  `OPEN_TASK_STATUSES` (`apps/core/views.py:66-70`).

**Risks.** There is **no `completed_at` column**, so analytics approximates
completion week from `updated_at` — the `AnalyticsView` docstring admits this
(`core/views.py:167-169`). Editing a completed task moves it to a different week
in the chart. `start_date`, `estimated_hours` and `labels` are dead weight today.

---

## 6. `documents_document`

`backend/apps/documents/models.py:20`

| Column | Type | Null | Key | Default | Purpose |
|---|---|---|---|---|---|
| **[base]** all six | | | | | |
| `project_id` | UUID FK | yes | — | null | `SET_NULL` — a document can be workspace-level |
| `title` | varchar(255) | no | — | filename | Defaults to the uploaded filename |
| `description` | text | no | — | `""` | |
| `file` | varchar(100) FileField | no | — | — | Path, **not** the bytes. Upload path `documents/<workspace_id>/<filename>` |
| `file_type` | varchar(100) | no | — | `""` | Denormalised MIME type or extension |
| `file_size` | bigint | no | — | `0` | Denormalised byte count |
| `uploaded_by_id` | UUID FK → user | yes | — | request user | `SET_NULL` |

**Written by:** `DocumentViewSet` (multipart create, metadata-only PATCH).
`DocumentSerializer.create` populates `file_size`, `file_type`, `uploaded_by` and
the default title (lines 74-87).
**Read by:** document list/detail, project detail, `/ai` hub, the RAG pipeline.

**Downstream effect:** creating a row here fires
`knowledge/handlers.py::_on_document_created`, which enqueues embedding — but
**only on create**, and only if the extension is supported. Replacing the file on
an existing document does *not* re-embed; that is what `reindex` is for.

**Risks.** No `max_length` guard, no MIME whitelist and no size limit are enforced
server-side — see [18-security.md](18-security.md). `file_type` is taken from the
client-supplied `content_type` when present, so it is not trustworthy.

---

## 7. `handovers_handover`

`backend/apps/handovers/models.py:20`

| Column | Type | Null | Key | Default | Purpose |
|---|---|---|---|---|---|
| **[base]** all six | | | | | |
| `task_id` | UUID FK | no | idx | — | `CASCADE`, `related_name="handovers"` |
| `from_user_id` | UUID FK → user | yes | — | submitter | `SET_NULL` |
| `to_user_id` | UUID FK → user | yes | — | — | The proposed new assignee |
| `summary` | text | no | — | — | **Required.** What was done |
| `pending_items` | text | no | — | `""` | What is left |
| `resources` | text | no | — | `""` | Links, credentials, context |
| `status` | varchar(20) | no | idx | `pending` | `pending`/`approved`/`rejected` |
| `reviewer_id` | UUID FK → user | yes | — | null | Set by the review action |
| `review_comment` | text | no | — | `""` | Mandatory when rejecting |
| `reviewed_at` | timestamptz | yes | — | null | Used by the average-review-time metric |

Indexes: `(workspace, status)`, `(task, status)`.

**Written by:** `HandoverViewSet` create/update/destroy and the `review` action.
**Read by:** handover list, reviewer queue, detail page, PDF export, dashboard
"pending handovers", analytics.

**Business rules** (all in [modules/handovers.md](modules/handovers.md)):
- `workspace` derived from the task; the task can never be swapped after creation.
- You cannot hand a task to yourself.
- The recipient must be a workspace member.
- Only the submitter may edit, and only while `pending`.
- Only `pending` handovers can be deleted.
- Only `REVIEWER_ROLES` may review, and only once.
- Rejection requires a comment.
- **Approval reassigns `Task.assignee`** — the only cross-table write in the app.

**Risk:** nothing prevents two pending handovers on the same task. There is no
uniqueness constraint or state check for that.

---

## 8. `comments_comment`

`backend/apps/comments/models.py:17`

| Column | Type | Null | Key | Default | Purpose |
|---|---|---|---|---|---|
| **[base]** `id`, `created_at`, `updated_at` | | | | | |
| `workspace_id` | UUID FK | no | idx | — | Declared directly, not inherited |
| `author_id` | UUID FK → user | no | — | — | **`CASCADE`** |
| `content` | text | no | — | — | Contains `@[Name](uuid)` mention tokens |
| `parent_id` | UUID FK → self | yes | — | null | Threading, `related_name="replies"` |
| `content_type_id` | int FK | no | idx-with | — | Generic target |
| `object_id` | UUID | no | idx-with | — | Generic target |
| `is_edited` | bool | no | — | `False` | Set by `perform_update` |
| `is_deleted` | bool | no | — | `False` | Soft delete |

Ordering is `("created_at",)` — **ascending**, unlike every other table, because
a thread reads oldest first.

**Delete is soft:** `destroy()` sets `is_deleted=True` **and blanks `content`**
(`views.py:103-108`), and `to_representation` returns `"[deleted]"`. The row
survives so replies keep their parent.

**Downstream:** every save re-syncs mentions; a save with a `parent_id` also
creates a `comment_reply` notification.

**Risk:** `author` is `CASCADE` while every comparable FK in the codebase is
`SET_NULL`. Deleting a user erases their comments and, through `parent` cascade,
other people's replies underneath them.

---

## 9. `mentions_mention`

`backend/apps/mentions/models.py:15`

| Column | Type | Null | Key | Default | Purpose |
|---|---|---|---|---|---|
| **[base]** three | | | | | |
| `comment_id` | UUID FK | no | unique-with | — | `CASCADE` |
| `mentioned_user_id` | UUID FK → user | no | unique-with | — | `CASCADE` |
| `workspace_id` | UUID FK | no | — | — | Denormalised from the comment |

Unique on `(comment, mentioned_user)`.

The denormalised `workspace_id` is documented in the model as being there for
cheap "my mentions in workspace X" reads (line 26).

**Written by:** `sync_comment_mentions()` only — never by a view.
**Read by:** `GET /mentions/` (read-only viewset).

---

## 10. `notifications_notification`

`backend/apps/notifications/models.py:26`

| Column | Type | Null | Key | Default | Purpose |
|---|---|---|---|---|---|
| **[base]** three | | | | | |
| `recipient_id` | UUID FK → user | no | idx-with | — | `CASCADE` |
| `actor_id` | UUID FK → user | yes | — | null | `SET_NULL`; null for system events |
| `workspace_id` | UUID FK | yes | — | null | Nullable — system notifications have none |
| `type` | varchar(32) | no | — | — | 8 choices (mention, task_assigned, comment_reply, workspace_invite, handover_submitted, handover_reviewed, task_updated, system) |
| `title` | varchar(255) | no | — | — | Pre-rendered headline |
| `message` | text | no | — | `""` | Truncated to 140 chars by callers |
| `link` | varchar(255) | no | — | `""` | **A frontend route**, e.g. `/handovers/<uuid>` |
| `is_read` | bool | no | idx-with | `False` | |

Index `(recipient, is_read)` supports the unread badge.

**Written by:** `create_notification()` only. Six call sites:
`handovers/views.py` (×3), `notifications/handlers.py` (×2 — mention, reply),
`invitations/views.py` (×1).

**Two rules inside `create_notification`** (`services.py:37-40`): a null recipient
returns `None`, and **self-notification is skipped** — you never get told about
your own action.

**Note on design:** `title` and `link` are *denormalised at write time*. That
means a task renamed after the fact still shows the old title in old
notifications — arguably correct for a notification feed, but worth knowing.

`NotificationType.task_updated` is defined but **never emitted** by any code path.

---

## 11. `activities_activity`

`backend/apps/activities/models.py:18`

| Column | Type | Null | Key | Default | Purpose |
|---|---|---|---|---|---|
| **[base]** three | | | | | |
| `actor_id` | UUID FK → user | yes | — | null | `SET_NULL` |
| `workspace_id` | UUID FK | no | idx-with | — | `CASCADE` |
| `action` | varchar(64) | no | — | — | Dotted string: `task.created`, `project.archived`, `member.invited`… |
| `content_type_id` | int FK | yes | idx-with | null | `SET_NULL`; **null for deletes** |
| `object_id` | UUID | yes | idx-with | null | Null for deletes |
| `metadata` | jsonb | no | — | `{}` | Human-readable snapshot |

Indexes `(workspace, created_at)`, `(content_type, object_id)`.

**Append-only.** Nothing in the codebase updates or deletes an activity row; the
only removal path is the workspace cascade.

**Written by:** signal handlers exclusively — never at a call site
(`models.py:4-6`). One exception: `invitations/views.py:123` calls `log_activity`
directly for `member.invited`, because no model save corresponds to that event.

**Read by:** `/activity` page, per-object timelines, CSV export, and the AI
activity summariser.

**Risk:** because it is signal-driven, any write that bypasses `post_save`
(`queryset.update()`, `bulk_create`, raw SQL, psql) is invisible to the audit
log. `NotificationViewSet.read_all` uses `.update()` — that is intentional, but it
is the pattern to watch for.

---

## 12. `invitations_invitation`

`backend/apps/invitations/models.py:40`

| Column | Type | Null | Key | Default | Purpose |
|---|---|---|---|---|---|
| **[base]** three | | | | | |
| `workspace_id` | UUID FK | no | idx-with | — | `CASCADE` |
| `email` | varchar(254) | no | — | — | Lower-cased on validate |
| `invited_by_id` | UUID FK → user | no | — | — | `CASCADE` |
| `role` | varchar(20) | no | — | `member` | Restricted to `INVITABLE_ROLES` |
| `status` | varchar(20) | no | idx-with | `pending` | pending/accepted/rejected/expired/cancelled |
| `token` | varchar(64) | no | **unique** | `secrets.token_urlsafe(32)` | **The credential.** Also the URL lookup key |
| `expires_at` | timestamptz | no | — | now + 7 days | Checked at accept time |

**The token is a bearer credential.** `lookup_field = "token"`, so
`/invitations/<token>/accept/` *is* the accept link.
`secrets.token_urlsafe(32)` gives ~256 bits of entropy — not guessable.

**Validation rules** (`serializers.py:45-61`): cannot invite an existing member;
cannot create a second pending invite for the same email in the same workspace.

**Expiry is lazy** — nothing sweeps expired rows. The status flips to `expired`
only when someone tries to accept (`views.py:159-162`), so a stale `pending` row
can sit past its `expires_at`. Any UI counting "pending invitations" will
over-count.

---

## 13. `knowledge_documentchunk`

`backend/apps/knowledge/models.py:22`

| Column | Type | Null | Key | Default | Purpose |
|---|---|---|---|---|---|
| **[base]** three | | | | | |
| `workspace_id` | UUID FK | no | idx | — | Denormalised from the document — **the tenant filter on the hot path** |
| `document_id` | UUID FK | no | unique-with | — | `CASCADE`, `related_name="chunks"` |
| `content` | text | no | — | — | The chunk text (~220 words) |
| `chunk_index` | int | no | unique-with | — | Order within the document |
| `token_count` | int | no | — | `0` | Word count approximation |
| `embedding` | **vector(384)** | yes | HNSW | null | The semantic vector |
| `metadata` | jsonb | no | — | `{}` | `{"title": "<document title>"}` |

The model docstring explains the denormalised `workspace_id` precisely: it lets
the tenant boundary be enforced with a single indexed filter on similarity
queries — the hot path for semantic search (lines 8-10).

**Written by:** `processor._store_chunks()` only — delete-all-then-`bulk_create`,
inside one transaction, batch size 200.
**Read by:** `semantic_search()`, `summarizer._gather_document()`,
`action_items._resolve_content()`, and `DocumentSerializer.get_chunk_count`.

**Risk:** `get_chunk_count` runs `obj.chunks.count()` per document, so a
20-document list page issues 20 extra COUNT queries — plus 20 more from
`get_embedding_status`. See
[19-performance-scalability.md](19-performance-scalability.md).

---

## 14. `knowledge_embeddingjob`

`backend/apps/knowledge/models.py:73`

| Column | Type | Null | Key | Default | Purpose |
|---|---|---|---|---|---|
| **[base]** three | | | | | |
| `workspace_id`, `document_id` | UUID FK | no | idx | — | `CASCADE` |
| `status` | varchar(20) | no | — | `pending` | pending/processing/completed/failed |
| `error` | text | no | — | `""` | Truncated to 2000 chars |
| `chunk_count` | int | no | — | `0` | Result summary |
| `provider` | varchar(64) | no | — | `""` | e.g. `sentence_transformer` |
| `model` | varchar(128) | no | — | `""` | e.g. `all-MiniLM-L6-v2` |
| `started_at`, `finished_at` | timestamptz | yes | — | null | Duration |

Index `(document, -created_at)` supports "latest job for this document", which is
exactly what `DocumentSerializer.get_embedding_status` asks for.

**Rows accumulate.** Every re-index creates a new job; nothing prunes old ones.
Small rows, but unbounded growth.

---

## 15. `ai_aiconversation` and `ai_aimessage`

`backend/apps/ai/models.py:17,41`

**`ai_aiconversation`** — `WorkspaceScopedModel` + `user_id` (`CASCADE`) +
`title` (varchar 255, defaults to the first 80 chars of the opening message).
Ordering `-updated_at`; index `(workspace, user, -updated_at)`.

Conversations are **private to their owner within the workspace** — the queryset
filters on `user=request.user` *and* workspace membership
(`ai/views.py:88-97`). A workspace admin cannot read someone else's chat.

**`ai_aimessage`** — `BaseModel` + `conversation_id` (`CASCADE`), `role`
(`user`/`assistant`/`system`), `content` (text), `sources` (jsonb list of the
retrieved chunks), `token_count` (int, written as `0` everywhere — never
populated), `metadata` (jsonb: confidence, top_score, model). Ordering
`created_at` ascending; index `(conversation, created_at)`.

The user message is persisted **before** the LLM call so history stays consistent
if generation fails (`ai/views.py:162-166`).

---

## 16. `ai_aisettings`

`backend/apps/ai/models.py:64`

| Column | Type | Null | Default | Purpose |
|---|---|---|---|---|
| **[base]** three | | | | |
| `workspace_id` | UUID **OneToOne** | no | — | One row per workspace |
| `is_enabled` | bool | no | `True` | Kill switch — `get_llm_provider` raises if false |
| `provider` | varchar(32) | no | `gemini` | gemini/openai/ollama |
| `chat_model` | varchar(128) | no | `gemini-3.6-flash` | |
| `embedding_provider` | varchar(32) | no | `sentence_transformer` | **Stored but not honoured** — see below |
| `embedding_model` | varchar(128) | no | `all-MiniLM-L6-v2` | Same |
| `temperature` | float | no | `0.2` | |
| `max_tokens` | int | no | `1024` | |
| `api_key_encrypted` | text | no | `""` | **Fernet-encrypted** |

Created lazily with `get_or_create` on first `GET /ai/settings/`
(`ai/views.py:332-334`). Only owners/admins may PATCH it.

**Encryption:** `apps/ai/services/crypto.py` uses Fernet (AES-128-CBC + HMAC).
The key comes from `AI_FIELD_ENCRYPTION_KEY`, or is derived deterministically
from `SECRET_KEY` via SHA-256 when unset. `decrypt()` swallows failures and
returns `""`, so a rotated key degrades to "no key configured" rather than
crashing. The production warning is in the module docstring: set a dedicated key
so rotating `SECRET_KEY` does not invalidate stored keys.

**Discrepancy worth knowing:** `embedding_provider` / `embedding_model` are
stored on this row, but `knowledge/embeddings/factory.py:35-36` reads
`settings.AI[...]` and **never** consults `AISettings`. Per-workspace embedding
configuration is therefore **not implemented** — which is consistent, since the
vector column's dimension is fixed at 384 for the whole database.

---

## 17. `ai_searchhistory` and `ai_prompttemplate`

**`ai_searchhistory`** — `BaseModel` + `workspace_id`, `user_id` (both
`CASCADE`), `query` (varchar 1000, truncated at write), `results_count` (int),
`top_score` (float). Index `(workspace, user, -created_at)`.
Written by `SearchView` on every semantic search; read by the "recent queries"
UI. Unbounded growth, and it **stores the raw query text** — a privacy
consideration if queries contain sensitive terms.

**`ai_prompttemplate`** — `WorkspaceScopedModel` + `name` (150), `description`
(text), `category` (64, default `general`), `template` (text), `is_shared` (bool,
default `True`). Ordering by `name`; index `(workspace, category)`.
The viewset narrows to `Q(is_shared=True) | Q(created_by=request.user)`
(`ai/views.py:134-137`), so private templates stay private.

---

## 18. SimpleJWT blacklist tables

Not defined in this codebase but load-bearing:

| Table | Role |
|---|---|
| `token_blacklist_outstandingtoken` | Every refresh token ever issued, with its user and expiry. Populated because `ROTATE_REFRESH_TOKENS` is on. |
| `token_blacklist_blacklistedtoken` | FK to an outstanding token; presence means "revoked". |

Written on logout (`RefreshToken(...).blacklist()`), on every rotation
(`BLACKLIST_AFTER_ROTATION`), and in bulk by `_blacklist_all_refresh_tokens()`
after a password reset.

**Operational note:** these tables grow with every refresh — a user active for a
week with 15-minute tokens generates hundreds of rows. SimpleJWT ships a
`flushexpiredtokens` management command; **nothing in this repository schedules
it.** No Celery beat schedule exists. Logged in
[25-known-limitations.md](25-known-limitations.md).

---

## 19. Cross-reference: who touches what

| Table | Written by | Read by (APIs) |
|---|---|---|
| `accounts_user` | register, profile PATCH, password reset, JWT last_login | almost every endpoint (nested) |
| `workspaces_workspace` | workspace CRUD, transfer-ownership | every scoped query |
| `workspaces_workspacemember` | workspace create, invitation accept, manage_member, transfer | **every permission check** |
| `projects_project` | project CRUD, archive/restore | projects, tasks, documents, dashboard, analytics, search, RAG |
| `tasks_task` | task CRUD, **handover approval** | tasks, projects, dashboard, analytics, search, RAG, handovers |
| `documents_document` | document upload/PATCH | documents, projects, AI hub, search |
| `handovers_handover` | handover CRUD + review | handovers, reviews, dashboard, analytics, PDF |
| `comments_comment` | comment CRUD + reply | task/project/document detail |
| `mentions_mention` | `sync_comment_mentions` signal only | `/mentions/` |
| `notifications_notification` | `create_notification` (6 call sites) | bell, notifications page, websocket |
| `activities_activity` | signal handlers + one direct call | activity page, timelines, CSV, AI summary |
| `invitations_invitation` | invitation CRUD + accept/reject/resend | invitations page, workspace settings |
| `knowledge_documentchunk` | `processor._store_chunks` only | AI search, chat, summarise, generate-tasks |
| `knowledge_embeddingjob` | `processor` | document serializer status field |
| `ai_*` | AI endpoints | AI pages |

---

**Next:** [11 — Data Flow](11-data-flow.md)
