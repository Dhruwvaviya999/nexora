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
{ "access": "<jwt>",
  "user": { "id": "<uuid>", "name": "...", "email": "...", ... } }
```

plus a header:

```
Set-Cookie: nexora_refresh=<jwt>; HttpOnly; Path=/api/v1/auth/; SameSite=Lax; Max-Age=604800
```

**There is no `refresh` in the body.** `LoginView.post` pops it out of the
serializer's output and hands it to `set_refresh_cookie`, so the long-lived
credential never reaches JavaScript:

```python
def post(self, request, *args, **kwargs):
    response = super().post(request, *args, **kwargs)
    if response.status_code == status.HTTP_200_OK:
        refresh = response.data.pop("refresh", None)
        if refresh:
            set_refresh_cookie(response, refresh)
    return response
```

The `user` key is the point of the custom serializer — five lines that save a
follow-up `/auth/me/` call on every login.

Side effects: `UPDATE_LAST_LOGIN = True` writes `accounts_user.last_login`, and
an `OutstandingToken` row is created for the refresh token.

**Errors** — `401` `{"detail": "No active account found with the given
credentials"}` · `400` missing fields · `429` throttled

**Chain**
`login-form.tsx` → `useAuth().login` → `authApi.login` →
`apiClient.post(..., {skipAuth:true})` → `LoginView` →
`EmailTokenObtainPairSerializer` → **cookie set by the server** →
`tokenStorage.setAccess(res.access)` (memory) → `setUser()` →
`router.replace(next ?? "/dashboard")`

---

## `POST /auth/refresh/`

| | |
|---|---|
| **Auth** | Public — the refresh cookie *is* the credential |
| **View** | `CookieTokenRefreshView` (custom; replaces SimpleJWT's `TokenRefreshView`) |

**Request** — an empty body. The token is read from the httpOnly cookie:

```http
POST /api/v1/auth/refresh/
Cookie: nexora_refresh=<jwt>
Content-Type: application/json

{}
```

**Response `200`**
```json
{ "access": "<jwt>" }
```
plus a `Set-Cookie` carrying the **rotated** refresh token.

`ROTATE_REFRESH_TOKENS` is on, so a new refresh token is issued every time and
the old one is blacklisted immediately — but it goes straight back into the
cookie rather than into the body:

```python
data = dict(serializer.validated_data)
rotated = data.pop("refresh", None)      # never returned to the client
response = Response(data, status=200)
if rotated:
    set_refresh_cookie(response, rotated)
```

**Body fallback.** `read_refresh_token` checks the cookie first, then
`request.data["refresh"]`. Browsers use the cookie; mobile and CLI clients,
which have no cookie jar, post the token explicitly.

**Errors** — `401 {"detail": "No refresh token provided."}` when neither is
present · `401` when the token is expired, blacklisted or malformed.

**Called only by** `refreshAccessToken()` in `lib/api/client.ts`, never by a
hook. Concurrent 401s share one in-flight call via `refreshPromise` — which
matters more than ever, since the cookie is shared browser state and rotation
makes the token single-use.

On failure the client calls `tokenStorage.clear()`, which drops the in-memory
access token and the session marker, and the app redirects to `/login`.

---

## `POST /auth/logout/`

| | |
|---|---|
| **Auth** | `IsAuthenticated` |
| **View** | `LogoutView(APIView)` |

**Request** — an empty body; the token comes from the cookie.
`{"refresh": "<jwt>"}` is still accepted for non-browser clients.

**Response `205 Reset Content`**, with a `Set-Cookie` that clears
`nexora_refresh`.

**The cookie is cleared on every path**, including both failure paths — a
client must always be able to end its own session locally, even if the token
was already invalid:

```python
token = read_refresh_token(request)
if not token:
    return clear_refresh_cookie(Response({"detail": "No refresh token provided."}, 400))
try:
    RefreshToken(token).blacklist()
except TokenError:
    return clear_refresh_cookie(Response({"detail": "Invalid or expired token."}, 400))
return clear_refresh_cookie(Response(status=205))
```

`clear_refresh_cookie` passes the same `path`, `domain` and `samesite` used
when setting it — Django's `delete_cookie` requires that, or the browser keeps
the original and logout silently fails.

**Client side** — the request is best-effort; a `finally` block always runs:

```ts
tokenStorage.clear();     // in-memory token + session marker
setUser(null);
queryClient.clear();      // critical: no stale data for the next user
router.replace(ROUTES.login);
```

**What it does not do:** the current *access* token stays valid until it
expires (up to 15 minutes) — inherent to stateless JWT. Other devices are
unaffected.

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

**Three side effects that matter:**

```python
_blacklist_all_refresh_tokens(user)      # every outstanding session is revoked
queue_templated_email(template="password_changed", ...)
return clear_refresh_cookie(Response(...))   # and this browser's cookie too
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

set automatically by `lib/api/client.ts` unless `skipAuth` is passed (login,
register, refresh). Every request also goes out with `credentials: "include"`,
so the browser can attach the refresh cookie — which, being path-scoped to
`/api/v1/auth/`, is only actually transmitted to refresh and logout.

This requires `CORS_ALLOW_CREDENTIALS = True` on the API, which is safe because
`CORS_ALLOWED_ORIGINS` is an explicit list (browsers forbid credentials with a
wildcard origin).

**WebSocket** authentication is different — the browser cannot set headers, so
the token rides in the query string:

```
ws://host:8000/ws/notifications/?token=<access>
```

Validated by `apps/common/channels_auth.py`, behind an `OriginValidator` checked
against `CORS_ALLOWED_ORIGINS`. See
[collaboration.md](collaboration.md#websocket).
