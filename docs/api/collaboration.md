# API — Comments, Mentions, Notifications & WebSocket

[← API index](README.md) · [Module deep dive](../modules/collaboration.md)

---

# Comments — `/api/v1/comments/`

`CommentViewSet(viewsets.ModelViewSet)` — **not** a `WorkspaceScopedViewSet`,
because the workspace is derived from the comment's target.

```python
def get_permissions(self):
    # Posting and replying only require membership (enforced in perform_create);
    # the author/admin object check is for edit/delete.
    if self.action in ("create","reply","list","retrieve"):
        return [IsAuthenticated()]
    return [IsAuthenticated(), IsAuthorOrWorkspaceAdmin()]
```

## `GET /comments/?target_type=&target_id=`

**Scope:** `filter(workspace__members__user=self.request.user).distinct()`

| Param | Values |
|---|---|
| `target_type` | `project` · `task` · `document` — anything else is ignored |
| `target_id` | UUID of the target |

The whitelist maps the public string to a `ContentType` natural key:

```python
ALLOWED_TARGETS = {
    "project":  ("projects", "project"),
    "task":     ("tasks", "task"),
    "document": ("documents", "document"),
}
```

**Ordering is `created_at` ascending** — unlike every other list in the API,
because a thread reads oldest-first.

**Response** — paginated `CommentSerializer`:

```json
{ "id": "<uuid>",
  "content": "Can you check this? @[Asha Rao](3f2c...)",
  "author": { ...UserSerializer... },
  "parent": null,
  "reply_count": 2,
  "is_edited": false, "is_deleted": false,
  "created_at": "...", "updated_at": "..." }
```

Deleted comments come back as `"content": "[deleted]"` via
`to_representation`.

> `reply_count` uses `source="replies.count"` — one query per comment.

## `POST /comments/`

**Request** — two shapes.

New comment on a target:
```json
{ "target_type": "task", "target_id": "<uuid>", "content": "..." }
```

Reply (target is inherited from the parent):
```json
{ "parent": "<comment uuid>", "content": "..." }
```

`target_type` and `target_id` are **write-only** and never appear in a response.

**Resolution** (`_resolve_target`, `views.py:61-89`):

| Check | Failure |
|---|---|
| Parent is not soft-deleted | `400 {"parent": ["Cannot reply to a deleted comment."]}` |
| `target_type` **and** `target_id` present when there is no parent | `400 {"target_type": ["target_type and target_id are required."]}` |
| `target_type` in the whitelist | `KeyError` → 500 if a bogus value reaches create; the serializer's `ChoiceField` normally rejects it first |
| Content is non-blank after strip | `400 {"content": ["Comment cannot be empty."]}` |
| Caller is a member of the **target's** workspace | `403 "You are not a member of this workspace."` |

`author`, `workspace`, `content_type` and `object_id` are all set server-side.

**Response `201`.**

**Side effects:** `comment.created` audit row; mention sync; a
`COMMENT_REPLY` notification when `parent_id` is set; a `MENTION` notification per
new mention; a websocket push per notification.

## `POST /comments/{id}/reply/`

Convenience wrapper — takes `{ "content": "..." }` and injects the parent:

```python
serializer = self.get_serializer(
    data={"content": request.data.get("content",""), "parent": str(parent.pk)})
```

Returns `201`.

## `PATCH /comments/{id}/`

**Auth: the author only** (`IsAuthorOrWorkspaceAdmin` — non-safe methods require
`obj.author_id == request.user.id`).

Sets `is_edited = True` via `perform_update`.
Re-runs the mention sync, so mentions added or removed by the edit are
reconciled — and only genuinely new ones notify.

## `DELETE /comments/{id}/` — soft

**Auth:** the author, **or** a workspace owner/admin (moderation):

```python
if request.method == "DELETE":
    member = obj.workspace.members.filter(user=request.user).first()
    return member is not None and member.role in (OWNER, ADMIN)
```

```python
comment.is_deleted = True
comment.content = ""          # the content is genuinely erased
comment.save(update_fields=["is_deleted","content","updated_at"])
return Response(status=204)
```

The row survives so reply chains stay intact. Blanking the content also clears
the comment's mentions on the next sync.

---

# Mentions — `/api/v1/mentions/`

`MentionViewSet(viewsets.ReadOnlyModelViewSet)` — **list and retrieve only.**
Mentions are never created through the API; `sync_comment_mentions()` owns them.

## `GET /mentions/?workspace=<uuid>`

**Scope:** `filter(mentioned_user=self.request.user)` — you only ever see
mentions **of you**.

```python
.select_related("comment", "comment__author", "mentioned_user", "workspace")
```

**Response** — paginated `MentionSerializer`.

---

# Notifications — `/api/v1/notifications/`

`NotificationViewSet(ListModelMixin, RetrieveModelMixin, GenericViewSet)` —
no create, update or delete.

## `GET /notifications/`

**Scope:** `filter(recipient=self.request.user).select_related("actor")`

**Filters** — hand-rolled in `get_queryset`, not django-filter:

| Param | Values |
|---|---|
| `is_read` | `"true"` / `"false"` (string comparison, exactly those two) |
| `type` | one of the 8 `NotificationType` values |
| `workspace` | UUID |

**Response** — paginated:

```json
{ "id": "<uuid>", "type": "handover_submitted",
  "title": "Asha handed over \"Fix billing sync\"",
  "message": "Migrated the webhook handler...",
  "link": "/handovers/<uuid>",
  "is_read": false,
  "actor": { ...UserSerializer... },
  "workspace": "<uuid>|null",
  "created_at": "..." }
```

`link` is a **frontend route**, built by `link_for()`. `title` and `message` are
denormalised at write time, so a later rename does not change old notifications.

## `GET /notifications/unread-count/`

```json
{ "count": 3 }
```

Polled every 30s **only when the websocket is not connected**
(`hooks/use-notifications.ts:37`). Backed by the index
`notifications_notification(recipient, is_read)`.

## `PATCH /notifications/{id}/read/`

Idempotent:

```python
if not notification.is_read:
    notification.is_read = True
    notification.save(update_fields=["is_read","updated_at"])
return Response(self.get_serializer(notification).data)
```

`200` with the notification.

## `PATCH /notifications/read-all/`

```python
updated = Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
return Response({"updated": updated}, status=200)
```

```json
{ "updated": 7 }
```

**Uses `queryset.update()`** — one SQL UPDATE, **no `post_save` signals**. That is
intentional here (notifications are not audited), but it is the pattern to
remember when adding audited models.

---

# WebSocket — `/ws/notifications/`

**Not** under `/api/v1/`. Mounted at the root
(`apps/notifications/routing.py`), which is why
`frontend/src/lib/realtime.ts` **replaces** the pathname of
`NEXT_PUBLIC_API_URL` rather than appending to it.

## Connecting

```
ws://localhost:8000/ws/notifications/?token=<access token>
wss://api.example.com/ws/notifications/?token=<access token>
```

```ts
const api = new URL(env.NEXT_PUBLIC_API_URL);
api.protocol = api.protocol === "https:" ? "wss:" : "ws:";
api.pathname = "/ws/notifications/";
api.search   = `?token=${encodeURIComponent(token)}`;
```

The token is in the query string because the browser `WebSocket` API cannot set
an `Authorization` header. Mitigations documented in
`apps/common/channels_auth.py:4-8`: wss in production, 15-minute token lifetime.

## Handshake

| Stage | Component | Behaviour |
|---|---|---|
| 1 | `OriginValidator` | Origin must be in **`CORS_ALLOWED_ORIGINS`** (not `ALLOWED_HOSTS`). A missing Origin is refused |
| 2 | `JWTAuthMiddleware` | Parses `?token=`, validates with SimpleJWT, sets `scope["user"]`. Anonymous is allowed through — the consumer decides |
| 3 | `NotificationConsumer.connect` | Anonymous → `close(4401)`. Otherwise joins group `notifications.<uuid-without-hyphens>` and sends `{"type":"connected"}` |

Accept-then-close is deliberately avoided: it would look like success to the
client.

## Messages — server → client

```json
{ "type": "connected" }
{ "type": "notification", "notification": { ...NotificationSerializer... } }
{ "type": "unread_count", "count": 4 }
{ "type": "pong" }
```

## Messages — client → server

Only one is handled:

```json
{ "type": "ping" }
```
→ `{"type": "pong"}`. Present so clients can keep the socket warm through proxies
that cut idle connections. **The socket is otherwise push-only** — marking read
still goes through REST, which *"keeps one code path for permissions and
auditing."*

## What the client does with a message

```ts
if (payload.type === "notification" || payload.type === "unread_count") {
  queryClient.invalidateQueries({ queryKey: ["notifications"] });
}
```
`hooks/use-notification-socket.ts:74-78`

**The pushed payload is deliberately ignored.** The socket is a signal; the data
comes from REST — one source of truth, no cache drift.

## Close codes

| Code | Meaning | Client behaviour |
|---|---|---|
| `1000` | Normal — the component unmounted | Do not reconnect |
| `4401` | Unauthenticated (application-defined) | Retry at the **slowest** interval (30s) |
| anything else | Network / server | Backoff `1s → 2s → 5s → 10s → 30s` |

## Server-side push

```python
def push_to_user(user_id, message: dict) -> None:
    try:
        channel_layer = get_channel_layer()
        if channel_layer is None: return
        async_to_sync(channel_layer.group_send)(user_group(user_id), message)
    except Exception:
        logger.warning("Could not push realtime message to user %s", user_id, exc_info=True)
```

Everything is swallowed — *"a channel layer that is down must never break the
write that triggered it."* And the push itself is deferred to
`transaction.on_commit`.

## Multi-process warning

With `InMemoryChannelLayer` (the development default when `CHANNEL_LAYER_URL` is
unset) and more than one web process, **a notification created in process A never
reaches a socket held by process B**. Set `REDIS_URL` in any multi-process
deployment.
