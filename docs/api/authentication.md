# API — Authentication

[← API index](README.md) · [Deep dive](../08-authentication-authorization.md)

All under `/api/v1/auth/`. Routes: `backend/apps/accounts/urls.py`.
Views: `backend/apps/accounts/views.py`. Serializers: `.../serializers.py`.

---

## `POST /auth/register/`

| | |
|---|---|
| **Auth** | Public (`AllowAny`) |
| **Throttle** | `RegisterRateThrottle` — 5/hour per IP |
| **View** | `RegisterView(generics.CreateAPIView)` |
| **Serializer** | `RegisterSerializer` |

**Request**
```json
{ "name": "Asha Rao", "email": "asha@example.com",
  "password": "<hidden>", "password_confirm": "<hidden>" }
```

**Validation**
- `validate_email` — lower-cased and stripped; rejected if
  `User.objects.filter(email__iexact=...).exists()`
- `validate` — `password == password_confirm`
- The `password` field carries `validators=[validate_password]`, so Django's four
  validators run (similarity, min length, common password, numeric-only)

**Response `201`** — `UserSerializer`:
```json
{ "id": "<uuid>", "name": "Asha Rao", "email": "asha@example.com",
  "avatar": "", "is_active": true, "date_joined": "...",
  "created_at": "...", "updated_at": "..." }
```

> **No tokens are returned.** Registration does not log you in — the frontend
> sends the user to `/login`. There is also **no email verification step**.

**Errors** — `400` field errors · `429` throttled

**Chain**
`register-form.tsx` → `authApi.register` → `apiClient.post(..., {skipAuth:true})`
→ `RegisterView` → `RegisterSerializer.create` → `UserManager.create_user`
(hashes the password) → `accounts_user`

---

## `POST /auth/login/`

| | |
|---|---|
| **Auth** | Public |
| **Throttle** | `LoginRateThrottle` — 10/min **per IP** |
| **View** | `LoginView(TokenObtainPairView)` |
| **Serializer** | `EmailTokenObtainPairSerializer` |

**Request**
```json
{ "email": "asha@example.com", "password": "<hidden>" }
```

**Response `200`**
```json
{ "access": "<jwt>", "refresh": "<jwt>",
  "user": { "id": "<uuid>", "name": "...", "email": "...", ... } }
```

The `user` key is the whole point of the custom serializer — five lines that save
a follow-up `/auth/me/` call on every login:

```python
def validate(self, attrs):
    data = super().validate(attrs)
    data["user"] = UserSerializer(self.user).data
    return data
```

Side effect: `UPDATE_LAST_LOGIN = True`, so `accounts_user.last_login` is written,
and an `OutstandingToken` row is created for the refresh token.

**Errors** — `401` `{"detail": "No active account found with the given
credentials"}` · `400` missing fields · `429` throttled

**Chain**
`login-form.tsx:35` → `useAuth().login` (`auth-provider.tsx:58`) →
`authApi.login` → `apiClient.post(..., {skipAuth:true})` → `LoginView` →
`EmailTokenObtainPairSerializer` → `tokenStorage.set(access, refresh)` (cookies)
→ `setUser()` → `router.replace(next ?? "/dashboard")`

---

## `POST /auth/refresh/`

| | |
|---|---|
| **Auth** | Public — the refresh token *is* the credential |
| **View** | SimpleJWT's `TokenRefreshView`, re-exported unchanged |

**Request** `{ "refresh": "<jwt>" }`
**Response `200`** `{ "access": "<jwt>", "refresh": "<jwt>" }`

Both tokens come back because `ROTATE_REFRESH_TOKENS = True`. The **old refresh
token is blacklisted immediately** (`BLACKLIST_AFTER_ROTATION = True`), so it is
single-use.

**Called only by** `refreshAccessToken()` in `lib/api/client.ts:41-62`, never by
a hook. Concurrent 401s share one in-flight call via `refreshPromise`.

On failure the client calls `tokenStorage.clear()` and returns `null`, which ends
the retry and eventually redirects to `/login`.

---

## `POST /auth/logout/`

| | |
|---|---|
| **Auth** | `IsAuthenticated` |
| **View** | `LogoutView(APIView)` |

**Request** `{ "refresh": "<jwt>" }`
**Response `205 Reset Content`** — no body
**Errors** — `400 {"detail": "Invalid or expired token."}` on `TokenError`

**Blacklists only the supplied refresh token.** The current *access* token stays
valid until it expires (up to 15 minutes) — inherent to stateless JWT. Other
devices are unaffected.

**Client side** (`auth-provider.tsx:67-79`) — the request is best-effort; a
`finally` block always runs:

```ts
tokenStorage.clear();
setUser(null);
queryClient.clear();          // critical: no stale data for the next user
router.replace(ROUTES.login);
```

---

## `GET /auth/me/`

| | |
|---|---|
| **Auth** | `IsAuthenticated` |
| **View** | `MeView(generics.RetrieveUpdateAPIView)`, `get_object()` returns `request.user` |
| **Serializer** | `UserSerializer` (read) |

**Response `200`** — the full user object.

**Called in exactly one place:** `AuthProvider`'s mount effect
(`auth-provider.tsx:44`). It is what turns "I have a cookie" into "I am user X".

---

## `PATCH /auth/me/`

| | |
|---|---|
| **Serializer** | `ProfileUpdateSerializer` — **only `name` and `avatar`** |

**Request** `{ "name": "Asha R.", "avatar": "https://..." }`
**Response `200`** — the full `UserSerializer`, always:

```python
def update(self, request, *args, **kwargs):
    super().update(request, *args, **kwargs)
    return Response(UserSerializer(self.get_object()).data)
```

The two-field allow-list **is** the protection — a user cannot PATCH their own
`email`, `is_active` or `is_staff`.

> `avatar` is not validated server-side. Only the frontend zod schema checks it
> is a URL. See [18-security.md](../18-security.md).

---

## `POST /auth/password-reset/`

| | |
|---|---|
| **Auth** | Public |
| **Throttle** | `PasswordResetRateThrottle` — 5/hour **per IP**, deliberately not per email |
| **View** | `PasswordResetRequestView` |

**Request** `{ "email": "asha@example.com" }`

**Response `202 Accepted` — always the same, regardless of whether the account exists:**
```json
{ "detail": "If an account exists for that address, a reset link is on its way." }
```

The docstring states why: *"Saying 'no such user' here would turn this endpoint
into a way to test which email addresses are registered."*

**When the user exists:**

```python
uid, token = build_reset_credentials(user)      # urlsafe_b64(pk), default_token_generator
queue_templated_email(
    template="password_reset",
    subject="Reset your Nexora password",
    to=user.email,
    context={"name": ..., "email": ...,
             "reset_url": frontend_url(f"/reset-password?uid={uid}&token={token}"),
             "valid_for": timeuntil(now() + PASSWORD_RESET_TIMEOUT, now())})
```

The queue is deferred to `transaction.on_commit`. Only `is_active=True` users are
matched.

**Throttle-key note:** keying on the submitted email would let an attacker lock a
specific person out of password resets (`throttling.py:29-32`).

---

## `POST /auth/password-reset/confirm/`

| | |
|---|---|
| **Auth** | Public |
| **Throttle** | 5/hour per IP |
| **Serializer** | `PasswordResetConfirmSerializer` |

**Request**
```json
{ "uid": "<b64>", "token": "<token>",
  "password": "<hidden>", "password_confirm": "<hidden>" }
```

**Validation, all inside the serializer** — deliberately, so an invalid link and
a mismatched password are reported the same way, as field errors:

1. Passwords match.
2. `urlsafe_base64_decode(uid)` → `User.objects.get(pk=...)`. Catches
   `TypeError`, `ValueError`, `OverflowError`, `User.DoesNotExist` **and Django's
   `ValidationError`** — the PK is a UUID, so a malformed `uid` fails inside the
   query rather than simply matching nothing.
3. `default_token_generator.check_token(user, token)`.
4. Django's password validators via `validators=[validate_password]`.

**Response `200`**
```json
{ "detail": "Password updated. You can sign in with your new password." }
```

**Two side effects that matter:**

```python
_blacklist_all_refresh_tokens(user)      # every outstanding session is revoked
queue_templated_email(template="password_changed", ...)
```

The revocation comment: *"Refresh tokens outlive the reset by days, so anyone
holding one (including whoever prompted the reset) keeps access unless they are
revoked."*

**Errors** — `400 {"password_confirm": ["Passwords do not match."]}` ·
`400 {"non_field_errors": ["This password reset link is invalid or has expired."]}`

The token self-invalidates: `default_token_generator` derives its hash from the
password hash and `last_login`, so a used or superseded link stops working.

---

## Authentication on other endpoints

Every other endpoint in the API expects:

```
Authorization: Bearer <access token>
```

set automatically by `lib/api/client.ts:78-81` unless `skipAuth` is passed
(login, register, refresh).

**WebSocket** authentication is different — the browser cannot set headers, so
the token rides in the query string:

```
ws://host:8000/ws/notifications/?token=<access>
```

Validated by `apps/common/channels_auth.py`, behind an `OriginValidator` checked
against `CORS_ALLOWED_ORIGINS`. See
[collaboration.md](collaboration.md#websocket).
