# API — Workspaces, Members & Invitations

[← API index](README.md) · [Module deep dive](../modules/workspaces.md)

`backend/apps/workspaces/views.py` · `backend/apps/invitations/views.py`

---

## Permission matrix

`WorkspaceViewSet` is the only viewset with a per-action matrix:

```python
def get_permissions(self):
    if   self.action in ("update","partial_update"): perms = [IsAuthenticated, IsWorkspaceAdminOrReadOnly]
    elif self.action == "destroy":                   perms = [IsAuthenticated, IsWorkspaceOwner]
    elif self.action in ("retrieve","members"):      perms = [IsAuthenticated, IsWorkspaceMember]
    else:                                            perms = [IsAuthenticated]      # list, create
    return [perm() for perm in perms]
```

---

## `GET /workspaces/`

**Auth:** any authenticated user — returns only workspaces they belong to.

```python
Workspace.objects.filter(members__user=self.request.user)
    .select_related("owner").prefetch_related("members").distinct()
```

**Response** — paginated `WorkspaceSerializer`:

```json
{ "id": "<uuid>", "name": "Aurora Labs", "slug": "aurora-labs",
  "description": "", "owner": { ...UserSerializer... },
  "role": "admin",            // ← YOUR role, computed per request
  "member_count": 7,
  "created_at": "...", "updated_at": "..." }
```

`role` is a `SerializerMethodField` resolved against `context["request"].user`:

```python
def get_role(self, obj):
    request = self.context.get("request")
    if not request or not request.user.is_authenticated: return None
    member = obj.members.filter(user=request.user).first()
    return member.role if member else None
```

**This field drives the entire frontend role UI** — the sidebar's Reviews link
and the handover review card both read `activeWorkspace.role`.

> `member_count` uses `source="members.count"`, which is one extra query per
> workspace. See [19](../19-performance-scalability.md).

---

## `POST /workspaces/`

**Auth:** any authenticated user.
**Request** `{ "name": "Aurora Labs", "description": "" }`
**Response `201`**

```python
@transaction.atomic
def perform_create(self, serializer):
    workspace = serializer.save(owner=self.request.user)
    WorkspaceMember.objects.create(workspace=workspace, user=self.request.user,
                                   role=WorkspaceRole.OWNER)
```

Atomic, because a workspace with no owner member would be unreachable — the
scoped queryset joins through membership, so the creator could not even read
their own workspace.

`slug` is generated in `Workspace.save()` and de-duplicated with `-2`, `-3`…
**Slugs are globally unique** (unlike project slugs, which are per-workspace).

Also fires `workspace.created` and `member.*` audit rows.

---

## `GET / PATCH / DELETE /workspaces/{id}/`

| Method | Who | Notes |
|---|---|---|
| GET | member | 404 if you are not a member |
| PATCH | owner / admin | `IsWorkspaceAdminOrReadOnly` — members may read, only owner/admin may write |
| DELETE | **owner only** | `IsWorkspaceOwner` |

Editable fields: `name`, `description`. `slug` and `owner` are read-only —
ownership changes go through `transfer-ownership`.

**DELETE cascades into everything** in the workspace. Activity logging is
suppressed during the cascade to avoid FK violations — see
[modules/activity-audit.md](../modules/activity-audit.md#7-the-cascade-delete-guard).

---

## `GET /workspaces/{id}/members/`

**Auth:** member

```json
[ { "id": "<member uuid>",
    "user": { "id": "<user uuid>", "name": "...", "email": "...", "avatar": "" },
    "role": "manager",
    "joined_at": "..." } ]
```

**Not paginated** — it is a plain `Response(serializer.data)`, not a list route.
Fine for normal team sizes.

Used by the workspace settings page and by the assignee dropdowns on
`/tasks` and `/activity`.

---

## `PATCH / DELETE /workspaces/{id}/members/{member_id}`

One action, two verbs, routed by regex:

```python
@action(detail=True, methods=["patch","delete"],
        url_path=r"members/(?P<member_id>[0-9a-fA-F-]+)")
def manage_member(self, request, pk=None, member_id=None): ...
```

**Auth:** owner / admin — checked inline (`views.py:99-101`), not by a permission
class.

| Rule | Failure |
|---|---|
| Caller is owner or admin | `403 "Only workspace owners and admins can manage members."` |
| Target member exists in this workspace | `404` via `get_object_or_404` |
| **Target is not the owner** | `400 "The owner's membership can't be changed here — use transfer-ownership."` |
| PATCH role ∈ {admin, manager, member} | `400 {"role": ["Role must be 'admin', 'manager', or 'member'."]}` |

**PATCH** `{ "role": "manager" }` → `200` with the updated member.
**DELETE** → `204`. Removal is logged as `member.removed` by the signal on
`WorkspaceMember`.

---

## `POST /workspaces/{id}/transfer-ownership/`

**Auth:** the **current owner only**.

**Request** `{ "user_id": "<uuid>" }`

| Check | Failure |
|---|---|
| Caller is the owner | `403 "Only the current owner can transfer ownership."` |
| `user_id` present | `400 {"user_id": ["user_id is required."]}` |
| Target is a member | `400 {"user_id": ["That user is not a member of this workspace."]}` |
| Target is not you | `400 "You already own this workspace."` |

```python
with transaction.atomic():
    target.role = OWNER;  target.save(update_fields=["role","updated_at"])
    actor.role  = ADMIN;  actor.save(update_fields=["role","updated_at"])
    workspace.owner_id = target.user_id
    workspace.save(update_fields=["owner","updated_at"])
```

**Three writes, one transaction.** A partial application would leave two owners
or none. The old owner is demoted to **admin**, not removed.

**Response `200`** — the workspace, re-serialised with `context={"request": request}`
so `role` reflects the caller's *new* role.

---

# Invitations

Base `/api/v1/invitations/`. `lookup_field = "token"` — **the token is both the
credential and the URL key.**

`http_method_names = ["get","post","delete","head","options"]` — no PATCH/PUT.

---

## `GET /invitations/`

**Scope** — an OR of two conditions:

```python
Invitation.objects.filter(
    Q(email__iexact=user.email)
    | Q(workspace__members__user=user,
        workspace__members__role__in=(OWNER, ADMIN))
).select_related("workspace","invited_by").distinct()
```

So you see invitations **addressed to you**, plus all invitations for workspaces
you administer.

**Extra params:** `?mine=true` (only yours), `?workspace=`, `?status=`

**Response** — paginated `InvitationSerializer`:

```json
{ "id": "<uuid>", "workspace": "<uuid>", "workspace_name": "Aurora Labs",
  "email": "ben@example.com", "role": "member", "status": "pending",
  "token": "<url-safe token>",
  "invited_by": { ...UserSerializer... },
  "expires_at": "...", "created_at": "..." }
```

The serializer comment notes the token *"is the accept/reject credential; only
ever returned to the scoped audience (workspace admins and the invited email)."*

---

## `POST /invitations/`

**Auth:** owner / admin (`_is_admin`, `views.py:66-71`)

**Request** `{ "workspace": "<uuid>", "email": "ben@example.com", "role": "member" }`

| Validation | Failure |
|---|---|
| `email` lower-cased and stripped | — |
| `role ∈ INVITABLE_ROLES` (admin/manager/member) | `400 "Members can only be invited as admin, manager, or member."` |
| Not already a member | `400 {"email": ["That person is already a member of this workspace."]}` |
| No existing **pending** invite for that email + workspace | `400 {"email": ["There is already a pending invitation for this email."]}` |

Token: `secrets.token_urlsafe(32)` (~256 bits). Expiry: now + 7 days.

**Side effects** (`_notify`, `views.py:77-114`):

1. If the invitee already has an account → in-app `WORKSPACE_INVITE`
   notification, link `/invitations`.
2. Always → `queue_templated_email("invitation", ...)` with
   `accept_url = FRONTEND_URL/invitations?token=<token>`, a `register_url`, and an
   `is_new_user` flag so the template can branch.
3. `log_activity("member.invited", metadata={email, role})` — a **direct** call,
   because no model save corresponds to this event.

The comment explains the two-channel design: *"The email is what reaches someone
who has no account yet — the in-app notification can only be created for a user
that already exists."*

---

## `POST /invitations/{token}/accept/`

**Auth:** the invited email only.

```python
def _require_recipient(self, invitation):
    if invitation.email.lower() != self.request.user.email.lower():
        raise PermissionDenied("This invitation was sent to a different email.")
```

| Check | Failure |
|---|---|
| Recipient matches | `403` |
| Status is `pending` | `400 "This invitation is no longer pending."` |
| Not expired | flips status to `expired`, then `400 "This invitation has expired."` |

```python
WorkspaceMember.objects.get_or_create(
    workspace=invitation.workspace, user=request.user,
    defaults={"role": invitation.role})
invitation.status = InvitationStatus.ACCEPTED
```

`get_or_create` makes accept **idempotent** — a double-click cannot duplicate a
membership (and the DB constraint would stop it anyway).

**Response `200`** with the updated invitation.

---

## `POST /invitations/{token}/reject/`

Same recipient and pending checks; sets status to `rejected`.

---

## `POST /invitations/{token}/resend/`

**Auth:** owner / admin.

| Check | Failure |
|---|---|
| Status ∈ {`pending`, `expired`} | `400 "Only pending or expired invitations can be resent."` |

Resets status to `pending`, sets a fresh 7-day `expires_at`, re-sends the email
and re-creates the in-app notification.

---

## `DELETE /invitations/{token}/`

**Auth:** owner / admin. Sets `status = cancelled` — **not** a row delete.
**Response `204`.**

---

## Expiry is lazy

Nothing sweeps expired invitations. The status flips only when someone tries to
accept, so a row can sit as `pending` past its `expires_at`. Any UI counting
"pending invitations" will over-count. Noted in
[25-known-limitations.md](../25-known-limitations.md).
