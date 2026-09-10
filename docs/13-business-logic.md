# 13 — Business Logic

[← Back to index](README.md)

Every non-CRUD rule in the codebase, in the format:

> **Rule** → where it lives → how it works → why it matters

Rules are grouped by domain. Anything that is just "save the row" is skipped.

---

## 1. Tenancy rules

### 1.1 You can only read objects in workspaces you belong to

**Where:** `backend/apps/common/viewsets.py:26-33`

```python
return self.queryset.filter(workspace__members__user=self.request.user).distinct()
```

**How:** every scoped queryset joins through `workspaces_workspacemember`. A row
in another tenant is simply not in the queryset, so `get_object()` raises 404.

**Why it matters:** this single line is the entire multi-tenant read guarantee. It
also means cross-tenant access returns **404, not 403** — the API never confirms
that an id exists in a workspace you cannot see.

### 1.2 You can only create objects in workspaces you belong to

**Where:** `WorkspaceScopedViewSet._require_membership` (`viewsets.py:35-39`)

Raises `ValidationError` when `workspace` is missing, `PermissionDenied` when you
are not a member. Note the queryset filter does not protect creates — this
explicit check does.

### 1.3 A child object's workspace is derived from its parent, never sent by the client

**Where:** `apps/tasks/serializers.py:76`, `apps/handovers/serializers.py:86`

```python
attrs["workspace"] = project.workspace     # Task
attrs["workspace"] = task.workspace        # Handover
```

Both declare `workspace = PrimaryKeyRelatedField(read_only=True)`.

**Why:** without this, a client could post `{project: <project in A>, workspace: B}`
and create an object whose workspace disagrees with its parent — poisoning every
scoped query.

### 1.4 People referenced on an object must be members of its workspace

**Where:** `apps/tasks/serializers.py:59-68` (assignee, reporter),
`apps/handovers/serializers.py:88-103` (recipient)

A valid user UUID is not enough; the user must have a `WorkspaceMember` row.

---

## 2. Workspace and membership rules

| Rule | Where | Detail |
|---|---|---|
| Creating a workspace makes you its owner **member** | `WorkspaceViewSet.perform_create` (`views.py:61-69`) | `@transaction.atomic`: workspace + `WorkspaceMember(role=OWNER)` together |
| Slugs auto-generate and de-duplicate | `Workspace._generate_unique_slug` (`models.py:49-56`) | `slugify(name)`, then `-2`, `-3`… until unique. Falls back to `"workspace"` for an unsluggable name |
| A person joins a workspace at most once | DB constraint `unique_workspace_member` | Enforced in the database, not just in code |
| The owner's membership cannot be edited via `manage_member` | `views.py:104-107` | Raises "use transfer-ownership". Prevents the owner accidentally demoting themselves and orphaning the workspace |
| Roles assignable via `manage_member` are `admin`/`manager`/`member` | `views.py:114-115` | `owner` is explicitly excluded |
| Ownership transfer demotes the old owner to admin | `views.py:145-151` | Three writes in one `transaction.atomic()` — promote, demote, update `workspace.owner_id` |
| You cannot transfer ownership to yourself | `views.py:142-143` | "You already own this workspace." |
| You cannot transfer to a non-member | `views.py:139-141` | |
| Only the owner may delete a workspace | `IsWorkspaceOwner` via `get_permissions` | Deleting cascades into everything |

---

## 3. Invitation rules

| Rule | Where |
|---|---|
| Only owners/admins may create, cancel or resend | `_is_admin()` (`invitations/views.py:66-71`) |
| Only the invited email address may accept or reject | `_require_recipient()` (line 73-75), case-insensitive |
| Cannot invite someone who is already a member | `InvitationSerializer.validate` (line 49-54) |
| Cannot create a second **pending** invite for the same email + workspace | same, line 55-60 |
| Only `admin`/`manager`/`member` are invitable | `validate_role` against `INVITABLE_ROLES` (`models.py:37`) — "ownership transfers are a separate flow" |
| Tokens are `secrets.token_urlsafe(32)` | `models.py:20-21` — ~256 bits, unguessable |
| Invitations expire 7 days after creation | `default_expiry()` (`models.py:24-25`) |
| Accepting an expired invite flips it to `expired` and fails | `views.py:159-162` |
| Resend only works on `pending` or `expired` invites | `views.py:145-146`; it resets `expires_at` to a fresh 7 days |
| Accept is idempotent on membership | `WorkspaceMember.objects.get_or_create(...)` (line 164-168) — accepting twice cannot duplicate |
| Cancel is a status change, not a delete | `destroy()` sets `status=CANCELLED` (line 135-137) |

**Expiry is lazy.** Nothing sweeps the table; the status only changes when
someone tries to accept. Pending-invite counts can therefore include expired
rows.

---

## 4. Task rules

| Rule | Where |
|---|---|
| `project` is required; `workspace` is derived from it | `TaskSerializer.validate` (line 70-76) |
| `reporter` defaults to the creating user | `TaskSerializer.create` (line 88-93) |
| Assignee and reporter must be workspace members | `_resolve_member` (line 59-68) |
| "Open" = `todo`, `in_progress`, `review` | `OPEN_TASK_STATUSES` (`core/views.py:66-70`) |
| "Overdue" = open **and** `due_date < today` | `core/views.py:120-122` |
| Deleting a project deletes its tasks | `on_delete=CASCADE` |
| Approving a handover reassigns the task | `handovers/views.py:116-120` |

**No status transition rules exist.** A task can go from `completed` straight
back to `todo`, or to `cancelled` and back. `TaskStatus` is a flat enum with no
state machine. Same for `ProjectStatus`.

---

## 5. Project rules

| Rule | Where |
|---|---|
| The creator owns the project by default | `ProjectSerializer.create` (line 41-46) |
| Slugs are unique **per workspace**, not globally | `unique_project_slug_per_workspace` constraint |
| `archive` / `restore` are dedicated actions, not a PATCH | `ProjectViewSet._set_archived` (line 23-38) |
| Archiving stamps `updated_by` | same |
| `archived` and `status` are independent | Dashboard counts them separately |

Why archive is an action rather than `PATCH {archived: true}`: it produces a
distinct, auditable intent and gives the frontend a single-purpose endpoint. Both
call `_set_archived`, so there is one implementation.

---

## 6. Handover rules ⭐

The densest rule set in the project. All in
`backend/apps/handovers/{serializers,views}.py`.

### At submission

| Rule | Where |
|---|---|
| `task` is required and its workspace becomes the handover's | `serializers.py:81-86` |
| `to_user` must be a workspace member | `serializers.py:90-98` |
| **You cannot hand a task to yourself** | `serializers.py:99-102` |
| `from_user` is always the requesting user | `serializers.py:107-111` |
| `summary` is required (`TextField` with no blank) | `models.py:38` |
| Status starts `pending` | `models.py:42-44` |
| The recipient is notified immediately | `views.py:49-58` |

### While pending

| Rule | Where |
|---|---|
| **Only the submitter may edit** | `perform_update` (`views.py:60-64`) |
| Editing is only possible while `pending` | `serializers.py:69-72` |
| **The task can never be swapped** after submission | `serializers.py:73-78` |
| Only `pending` handovers may be deleted | `perform_destroy` (`views.py:67-68`) |
| Delete is allowed for the submitter **or** a reviewer-role member | `views.py:69-73` |

### At review

| Rule | Where |
|---|---|
| Only `REVIEWER_ROLES` (owner/admin/manager) may review | `_reviewer_membership` (`views.py:40-45`, used at 87) |
| A handover may be reviewed **once** | `views.py:91-92` |
| **Rejecting requires a comment** | `HandoverReviewSerializer.validate` (`serializers.py:124-129`) |
| Decision must be `approved` or `rejected` — `pending` is not a valid decision | `ChoiceField` (`serializers.py:117-119`) |
| Approval sets `task.assignee = to_user` | `views.py:116-120` |
| Rejection leaves the task untouched | implicit — the `if approved` branch |
| Approval notifies the recipient (`TASK_ASSIGNED`) | `views.py:121-129` |
| Both outcomes notify the submitter (`HANDOVER_REVIEWED`) | `views.py:131-142` |
| `reviewer`, `review_comment`, `reviewed_at`, `updated_by` are all stamped | `views.py:99-113` |
| The approval guard also checks `to_user is not None` | `views.py:116` — the FK is `SET_NULL`, so a deleted user cannot crash the review |

### What is **not** enforced

- Nothing stops **two pending handovers on the same task**. Both could be
  approved in sequence, the second overwriting the first's assignment.
- The submitter is not required to be the task's current assignee. Anyone in the
  workspace can hand over anyone's task.

Both are listed in [25-known-limitations.md](25-known-limitations.md).

---

## 7. Comment rules

| Rule | Where |
|---|---|
| Only `project`, `task`, `document` accept comments | `ALLOWED_TARGETS` whitelist (`comments/serializers.py:10-14`) |
| Empty/whitespace comments are rejected | `validate_content` (line 57-61) |
| A reply inherits its parent's workspace and target | `_resolve_target` (`views.py:64-71`) |
| **You cannot reply to a deleted comment** | `views.py:67-68` |
| Posting requires workspace membership | `views.py:83-84` |
| Editing sets `is_edited = True` | `perform_update` (line 100-101) |
| Delete is **soft**: `is_deleted=True` and `content=""` | `destroy` (line 103-108) |
| Deleted comments render as `"[deleted]"` | `to_representation` (`serializers.py:63-67`) |
| Only the author may edit | `IsAuthorOrWorkspaceAdmin` |
| The author **or** a workspace owner/admin may delete | same, lines 24-29 |
| Threads read oldest-first | `Meta.ordering = ("created_at",)` |

Soft delete exists so reply chains stay intact — the reason is in the model
docstring (`comments/models.py:6`).

---

## 8. Mention rules

**Where:** `backend/apps/mentions/services.py`

| Rule | Detail |
|---|---|
| Token format | `@[Display Name](<user-uuid>)` — regex at line 23 |
| Only workspace members can be mentioned | `filter(workspace_memberships__workspace=comment.workspace)` |
| You cannot mention yourself | `.exclude(id=comment.author_id)` |
| Duplicate mentions collapse | DB constraint `unique_comment_mention` |
| **Sync is idempotent** | Adds new, removes ones deleted by an edit, and fires `user_mentioned` **only for new** mentions (lines 49-68) |
| Soft-deleting a comment clears its mentions | Its content becomes `""`, so the next sync finds none (`handlers.py:12`) |

Idempotency is the important property: editing a comment ten times does not send
ten notifications.

---

## 9. Notification rules

**Where:** `backend/apps/notifications/services.py:22-52`

| Rule | Detail |
|---|---|
| Null recipient → no notification | returns `None` |
| **Self-notification is skipped** | `if actor is not None and recipient.pk == actor.pk: return None` |
| The push is deferred to `transaction.on_commit` | So a rollback sends nothing, and the row is visible before the client refetches |
| Push failure is swallowed | `push_to_user` catches everything — realtime must never break the write |
| `link` is a **frontend route** | `link_for()` maps a content type to `/tasks/`, `/projects/`, `/documents/`, `/handovers/` |
| Marking read is idempotent | `if not notification.is_read:` guard (`views.py:56-59`) |
| Read-all uses `.update()` | Single UPDATE, no signals — returns `{"updated": n}` |

`NotificationType.TASK_UPDATED` is defined but never emitted anywhere.

---

## 10. Audit rules

**Where:** `backend/apps/activities/{handlers,services}.py`

| Rule | Detail |
|---|---|
| The actor is `created_by` on create, `updated_by` on update | `_audit_actor` (`handlers.py:24-26`) |
| Delete rows have **no target** | `content_type` and `object_id` are null — the object is gone |
| Metadata is a small human-readable snapshot | e.g. `{"title": ..., "status": ...}` — survives renames and deletes |
| Actions are dotted strings | `task.created`, `project.updated`, `handover.deleted`, `member.invited` |
| Soft-deleted comments are not logged as creates | `if not created or instance.is_deleted: return` (`handlers.py:60-61`) |
| **Activity is suppressed while a workspace is being deleted** | `_workspaces_being_deleted` set (`services.py:15-32`) |

That last one is a real bug fix. Without it, the cascade's `post_delete` handlers
would append activity rows referencing a workspace that is about to disappear —
a foreign-key violation at commit that would take the whole delete down. The
comment (`services.py:8-14`) spells it out, and notes the rows would be pointless
anyway since `Activity.workspace` cascades.

---

## 11. Document and ingestion rules

| Rule | Where |
|---|---|
| A file is required on create, optional on update | `DocumentSerializer.validate` (line 68-72) — enables metadata-only edits |
| Title defaults to the filename | `create` (line 86-87) |
| `file_size`/`file_type` are captured at upload | `create` (line 76-82) |
| Files are stored under `documents/<workspace_id>/<filename>` | `document_upload_path` (`models.py:15-17`) |
| Embedding is triggered **only on create** | `handlers.py:26` — metadata edits never re-embed |
| Only `.pdf .docx .txt .md .markdown` are processed | `SUPPORTED_EXTENSIONS` (`extractor.py:13`) |
| Unsupported files are skipped silently | `handlers.py:28-30` |
| Ingestion failure never fails the upload | broad `except` (`handlers.py:33-34`) |
| Re-indexing is atomic and replaces all chunks | `_store_chunks` (`processor.py:113-131`) |
| Failures are recorded on the job row | `process_document` except block (`processor.py:104-110`) |
| The `reindex` action returns 202 with job state | `documents/views.py:29-44` |

---

## 12. AI rules

| Rule | Where |
|---|---|
| Every AI endpoint resolves and authorises the workspace first | `resolve_workspace()` (`ai/permissions.py:15`) |
| Changing AI settings requires owner/admin | `require_admin=True` (`ai/views.py:346`) |
| Conversations are private to their owner | queryset filters `user=request.user` (`ai/views.py:88-97`) |
| Prompt templates: shared, or your own | `Q(is_shared=True) \| Q(created_by=request.user)` (line 134-137) |
| User input is sanitised and capped at 4000 chars | `security.sanitize_input` |
| Retrieved content is always fenced as untrusted | `security.wrap_untrusted` |
| Retrieval is always workspace-filtered | `semantic_search` (`search.py:52-54`) |
| Chunks further than 0.75 cosine distance are dropped | `SEARCH_MAX_DISTANCE` |
| Only the top 6 chunks are used | `SEARCH_TOP_K` |
| Chat history is the last 10 turns | `_HISTORY_TURNS` (`ai/views.py:48`) |
| The user message is saved **before** the LLM call | `ai/views.py:162-166` — history stays consistent on failure |
| AI is rate limited to 30/hour per user | `AIRateThrottle` — "LLM calls cost money per request" |
| A workspace can disable AI entirely | `AISettings.is_enabled` → `get_llm_provider` raises `ProviderError` |
| API keys are encrypted at rest | Fernet, `services/crypto.py` |
| Generated tasks are **not persisted** | `action_items.py:5-7` — returned for review; the frontend creates them via the Task API |
| Suggested priorities are coerced to valid values | `_parse` (`action_items.py:67-69`) defaults anything unknown to `medium` |
| Suggested due dates must match `YYYY-MM-DD` | `_DATE_RE` (line 70-72), else `null` |

The last three are important: the LLM's output is treated as **untrusted input**
and validated before it is allowed anywhere near the database.

---

## 13. Confidence scoring

**Where:** `backend/apps/ai/services/rag.py:89-94`

```python
def _confidence(top_score, has_structured):
    if top_score >= 0.6:                     return "high"
    if top_score >= 0.4 or has_structured:   return "medium"
    return "low"
```

`top_score` is `1 - cosine_distance` of the best-matching chunk. Rendered by
`components/ai/confidence-badge.tsx`.

**Why it matters:** it tells the user how much of the answer was actually
grounded in their documents. `has_structured` bumps a weak retrieval to
"medium" because the model still had real project/task data to work from.

---

## 14. Analytics definitions

**Where:** `backend/apps/core/views.py:163-260`

| Metric | Definition |
|---|---|
| Weekly window | The last **8 ISO weeks**, Monday-based, oldest first |
| `created` per week | Tasks whose `created_at` falls in that week |
| `completed` per week | Tasks with `status=completed` whose **`updated_at`** falls in that week |
| Workload | Top 8 assignees by count of **open** tasks |
| `avg_review_hours` | `Avg(reviewed_at - created_at)` over reviewed handovers, rounded to 1dp; `null` when none |

**The known approximation:** there is no `completed_at` column, so completion week
is inferred from `updated_at`. The view's own docstring admits it
(lines 167-169). Editing a long-completed task moves it into the current week's
bar. Fixing it means adding a `completed_at` column and setting it on the
transition.

---

## 15. Dashboard definitions

**Where:** `backend/apps/core/views.py:104-152`

| Stat | Definition |
|---|---|
| `active_projects` | `status=active` **and** `archived=False` |
| `pending_tasks` | status in (todo, in_progress, review) |
| `overdue_tasks` | open **and** `due_date < today` |
| `my_tasks` | open **and** `assignee = request.user` |
| `pending_handovers` | `status=pending` in this workspace — **not** filtered to ones you can review |

The last one is worth noting: a plain member sees a count of handovers they
cannot act on.

---

## 16. Frontend-side rules

Rules that live only in the UI. None of these are security boundaries.

| Rule | Where |
|---|---|
| Show "Reviews" nav only to reviewer roles | `app-sidebar.tsx:71-74` |
| Show the approve/reject card only to reviewer roles | `handovers/[id]/page.tsx:80-81` |
| Show Delete only to the submitter or a reviewer, and only while pending | `handovers/[id]/page.tsx:122` |
| Block queries until a workspace is chosen | `enabled: !!params.workspace` in every list hook |
| Show `<NoWorkspace/>` when the user belongs to none | Most pages, e.g. `dashboard/page.tsx:40` |
| Remember the active workspace across reloads and tabs | `workspace-provider.tsx` |
| Passwords must be 8-128 chars and match | `validations/auth.ts:16-25` |

The backend re-validates every one of these that matters.

---

**Next:** [14 — Algorithms](14-algorithms.md)
