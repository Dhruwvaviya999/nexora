# 18 — Security Review

[← Back to index](README.md)

A security-oriented review of what is actually implemented. **Nothing here is
called secure because a library is present** — every claim points at the code that
enforces it.

Three sections: **Implemented**, **Partially implemented**, **Missing / risk**.

---

## Part 1 — Implemented

### 1.1 Authentication

| Control | Evidence |
|---|---|
| Password hashing | Django default PBKDF2. `set_password()` in `UserManager._create_user` and `PasswordResetConfirmSerializer.save`. No custom `PASSWORD_HASHERS` in base/production |
| Password strength | Four validators enabled (`base.py:156-161`) and actually applied via `validators=[validate_password]` on both password fields |
| Short-lived access tokens | 15 minutes |
| Refresh rotation | `ROTATE_REFRESH_TOKENS = True` |
| Rotation blacklisting | `BLACKLIST_AFTER_ROTATION = True` — a refresh token is single-use |
| Logout revocation | `RefreshToken(...).blacklist()` |
| **Full session revocation on password reset** | `_blacklist_all_refresh_tokens()` (`accounts/views.py:188-191`) |
| Signing key separable from `SECRET_KEY` | `JWT_SIGNING_KEY` env var |
| No session auth on the API | `DEFAULT_AUTHENTICATION_CLASSES` is JWT only |

The password-reset revocation is the strongest single control here. Most projects
forget it. The comment states the threat precisely: refresh tokens outlive the
reset by days, so whoever prompted the reset keeps access unless they are revoked.

### 1.2 Authorization

| Control | Evidence |
|---|---|
| Private by default | `DEFAULT_PERMISSION_CLASSES = (IsAuthenticated,)`; only 4 views opt out |
| Tenant isolation on reads | `WorkspaceScopedViewSet.get_queryset()` filters through membership |
| Tenant isolation on writes | `_require_membership()` in `perform_create` |
| Tenant isolation on AI | `resolve_workspace()` called before any retrieval in all 5 AI action views |
| Tenant isolation on retrieval | `semantic_search` filters `workspace=workspace` **before** the vector scan |
| Role checks | Five permission classes + inline checks for handovers, invitations, AI settings |
| Object-level ownership | Comment edit is author-only; handover edit is submitter-only |
| Cross-tenant reads return **404**, not 403 | Consequence of queryset filtering — does not confirm an id exists |
| Relations validated against membership | `_resolve_member()` for assignee/reporter/recipient |
| Workspace derived, never client-supplied | Task and Handover serializers |
| Private AI conversations | Filtered by `user=request.user`; a workspace admin cannot read them |
| Private prompt templates | `Q(is_shared=True) \| Q(created_by=request.user)` |

**Tenant isolation is the strongest property of this codebase**, and it is
enforced in four independent places: the base queryset, the create check, the AI
gate and the vector search filter.

### 1.3 Injection

| Vector | Status | Why |
|---|---|---|
| SQL injection | **Not possible** | Zero raw SQL. No `.raw()`, no `cursor.execute`, no string-built queries. Every query is ORM-built and parameterised, including the pgvector `CosineDistance` annotation |
| XSS via React | **Mitigated** | React escapes by default and there is **no `dangerouslySetInnerHTML` anywhere** in `frontend/src` — verified |
| Template injection in email | **Mitigated correctly** | The `"text"` engine has autoescape off *only* for plain-text bodies; the HTML sibling renders through the default escaping engine |
| Prompt injection | **Defended in depth** | `sanitize_input` + `wrap_untrusted` + `SYSTEM_GUARDRAILS` + message ordering — see [14-algorithms.md](14-algorithms.md#4-prompt-injection-defence) |

### 1.4 Rate limiting

Six named scopes, all environment-tunable, all keyed sensibly:

- `login` 10/min **by IP** — so an attacker cannot get a fresh bucket per guessed
  email.
- `register` 5/hour by IP.
- `password_reset` 5/hour **by IP, deliberately not by email** — keying on the
  submitted address would let an attacker lock a specific person out of resets
  (`throttling.py:29-32`).
- `ai` 30/hour by user — LLM calls cost money.
- `anon` 60/min, `user` 1000/hour globally.

Counters live in Redis in production, which `base.py:222-226` explains is
necessary: a per-process `LocMemCache` makes the effective limit
`rate × worker_count`.

### 1.5 User enumeration

`PasswordResetRequestView` returns the **same 202 and the same body** whether or
not the account exists (`accounts/views.py:143-150`), and the docstring says why.

Note the contrast: `RegisterSerializer.validate_email` *does* reveal existence
("A user with this email already exists") — but that is unavoidable for a
registration form and is rate-limited to 5/hour.

### 1.6 CORS and websocket origin

```python
CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")     # explicit list, no wildcard
```

- `CorsMiddleware` sits second, above `CommonMiddleware`, as django-cors-headers
  requires.
- `CORS_ALLOW_ALL_ORIGINS` is **never** set.
- `CORS_ALLOW_CREDENTIALS` is **not** set — correct, since auth is a header, not a
  cookie.
- WebSockets are validated with `OriginValidator` against the same list, and a
  missing `Origin` header is refused.

The `asgi.py:37-41` comment on using `CORS_ALLOWED_ORIGINS` rather than
`ALLOWED_HOSTS` is a genuinely subtle correctness point: the socket's Origin is
the *frontend's*, while `ALLOWED_HOSTS` lists the *API's* hostnames.

### 1.7 Production hardening

`config/settings/production.py`

```python
DEBUG = False
SECURE_SSL_REDIRECT = True                 # env-overridable
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 30 days
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = (JSONRenderer,)   # no browsable API
```

Plus `XFrameOptionsMiddleware` (clickjacking) inherited from base.

### 1.8 Secrets handling

| Control | Evidence |
|---|---|
| Secrets from the environment | `django-environ`, never hard-coded |
| `.env` files gitignored | `.gitignore` lists `.env`, `backend/.env`, `frontend/.env` — **verified untracked** with `git ls-files` |
| Only placeholder examples committed | `.env.docker.example` and `backend/.env.example` contain no real values — verified |
| AI API keys encrypted at rest | Fernet (AES-128-CBC + HMAC), `ai/services/crypto.py` |
| API keys never returned in plaintext | `AISettings.api_key_encrypted`; the model exposes only `has_api_key` |
| `SECRET_KEY` has no default | `env("SECRET_KEY")` with `default=""` — an empty key fails Django's checks |
| Compose refuses to start without it | `SECRET_KEY: ${SECRET_KEY:?set SECRET_KEY in .env}` |

### 1.9 Container hardening

Both images run as **non-root** (`nexora` uid 1000, `nextjs` uid 1001). The
backend image purges `build-essential` and `libpq-dev` in the same layer they were
installed.

---

## Part 2 — Partially implemented

### 2.1 CSRF

`CsrfViewMiddleware` is enabled and `CSRF_COOKIE_SECURE = True` in production —
but the API authenticates with a **header**, not a cookie, so CSRF is
structurally not applicable to it: a cross-site request cannot forge an
`Authorization` header.

The middleware is doing real work only for the Django admin.

**However**, tokens *are* in cookies on the frontend origin. The mitigations
there are `SameSite=Lax` on the cookie and the fact that the API ignores cookies
entirely. That combination is sound. But it depends on the frontend never being
changed to send cookies to the API.

### 2.2 XSS

React escaping plus no `dangerouslySetInnerHTML` is a strong baseline. Two soft
spots:

1. `User.avatar` is an unvalidated URL server-side (`ProfileUpdateSerializer`
   applies no validator) and is rendered as `<AvatarImage src={user.avatar}>`.
   React will not execute a `javascript:` URL in `src`, so this is low risk, but
   it does allow arbitrary external image loading (tracking pixels, SSRF-ish
   probing from the viewer's browser).
2. Any future markdown renderer would need explicit sanitisation — the AI returns
   markdown and the prompts encourage it.

### 2.3 Input validation

Comprehensive for domain fields (see [13-business-logic.md](13-business-logic.md)),
with these gaps:

- **No file size limit** anywhere.
- **No upload MIME whitelist** — only extraction is restricted.
- `avatar` URL not validated server-side.
- `Comment.content` has no length cap — `TextField`, no `max_length`.
- `AIMessage.content` likewise.

### 2.4 Logging

`logger.warning` / `logger.exception` are used correctly and **no code logs a
token, password or API key** — verified. But there is no `LOGGING` configuration
at all, so output goes to Django's default console handler and nothing is
aggregated, rotated or alerted on.

One thing to watch: the websocket token is in the URL query string. Uvicorn's
access log format does not include query strings by default, but a reverse proxy
in front of it very well might. The code comment acknowledges this
(`channels_auth.py:4-8`).

---

## Part 3 — Missing / risk

Ordered by severity.

### 🔴 3.1 Tokens are readable by JavaScript (`httpOnly` not set)

**Where:** `frontend/src/lib/auth/token-storage.ts:12,18`

```ts
const COOKIE_OPTS = "path=/; SameSite=Lax";     // no HttpOnly, no Secure
document.cookie = `${name}=${encodeURIComponent(value)}; Max-Age=${MAX_AGE}; ${COOKIE_OPTS}`;
```

**Impact:** any XSS on the frontend origin can read both tokens and exfiltrate
them. The refresh token is valid for 7 days.

**Why it is like this:** cookies (not localStorage) so `proxy.ts` can read them
server-side. The file documents the trade-off and calls it "good enough for this
foundation".

**Note:** `httpOnly` cannot simply be added — the client-side code that sets and
reads them would break. The real fix is architectural: have the backend set an
httpOnly refresh cookie on login, keep the access token in memory only, and add a
refresh endpoint that reads the cookie. That also removes the need for
`proxy.ts` to read tokens at all.

**Mitigating factors:** no `dangerouslySetInnerHTML`, React escaping, and no
user-supplied HTML rendering path currently exists.

### 🔴 3.2 `Secure` flag not set on token cookies

Same file. Over plain HTTP the cookies are sent in cleartext. In practice the
production settings force HTTPS via `SECURE_SSL_REDIRECT`, but that is the
*backend's* redirect — it does not govern the frontend origin's cookies.

**Fix:** append `; Secure` when `location.protocol === "https:"`.

### 🟠 3.3 No file upload restrictions

Any authenticated workspace member can upload a file of **any type and any size**.
There is no `DATA_UPLOAD_MAX_MEMORY_SIZE` override, no MIME whitelist, no size
check in `DocumentSerializer`.

**Impact:** disk exhaustion; storing executables or HTML/SVG. In `DEBUG` mode
those become fetchable URLs on the API origin — an HTML file served from the API
origin is a stored-XSS vector against that origin.

**Fix:** a `validate_file` on the serializer checking size and extension, plus
`X-Content-Type-Options: nosniff` (already on in production) and
`Content-Disposition: attachment` when serving.

### 🟠 3.4 Edge guard does not cover most protected routes

`proxy.ts` matches only `/dashboard/*`, `/workspaces/*`, `/login`, `/register`.
Ten other authenticated route trees rely purely on the client-side layout gate.

**Impact:** no data exposure (there is no token, so every API call 401s), but the
protection story is inconsistent and a future page that renders server-side would
not be covered.

**Fix:** extend the matcher, or invert it to match everything except a public
allow-list.

### 🟠 3.5 AI endpoints leak workspace existence

`resolve_workspace()` returns **404** for a nonexistent workspace and **403** for
one you are not a member of (`ai/permissions.py:19-25`). Everywhere else in the
API, both cases return 404.

**Impact:** an authenticated user can probe UUIDs to learn which workspaces
exist. Low value given UUIDs are unguessable, but it is an inconsistency.

**Fix:** raise `NotFound` in both branches.

### 🟡 3.6 No account lockout, no MFA, no email verification

- Failed logins are throttled by IP but never lock an account.
- No 2FA of any kind.
- Registration creates an immediately usable account with **no email
  verification**, so anyone can register under an address they do not control.
  Combined with invitations being matched on `email__iexact`, someone could
  register with a colleague's address and accept invitations meant for them —
  though they would need to know the invite exists.

### 🟡 3.7 Blacklisted tokens are never pruned

`token_blacklist_outstandingtoken` grows with **every** refresh. SimpleJWT ships
`manage.py flushexpiredtokens`; nothing in this repository schedules it. No Celery
beat schedule exists at all.

**Impact:** unbounded table growth, and every token validation checks the
blacklist.

### 🟡 3.8 No security headers beyond Django's defaults

No Content-Security-Policy, no `Referrer-Policy`, no `Permissions-Policy` — on
either the Django side or in `next.config.ts` (which is an empty config object).

A CSP would meaningfully reduce the impact of risk 3.1.

### 🟡 3.9 No error tracking or audit of security events

Failed logins, throttle trips and permission denials are not recorded anywhere
queryable. The `activities_activity` table logs business events, not security
events. There is no way to answer "was this account under attack last Tuesday?"

### 🟡 3.10 `Workspace.owner` and `Comment.author` cascade on user delete

Deleting a user deletes every workspace they own — and all its content — and
every comment they wrote, plus replies underneath. There is no soft-delete or
ownership-reassignment path for users.

### 🟢 3.11 Minor

- Fernet key derived from `SECRET_KEY` when `AI_FIELD_ENCRYPTION_KEY` is unset;
  rotating `SECRET_KEY` then silently invalidates every stored API key. The
  module docstring warns about it.
- `.env.docker.example` ships `POSTGRES_PASSWORD=nexora` as a placeholder; a
  careless copy leaves a trivial database password.
- No `SECURE_REFERRER_POLICY` (Django 3.0+ default is `same-origin`, so this is
  actually covered by the framework default).

---

## Part 4 — Threat walkthroughs

### "An attacker steals a refresh token"

They get up to 7 days of access **until the real user's next refresh**, at which
point rotation + blacklisting means one of the two sessions dies. Nothing detects
or alerts on that. The user can kill it by resetting their password, which
revokes every outstanding refresh token. There is no "sign out everywhere" button.

### "An attacker gets XSS on the frontend"

Game over for that user: both tokens are readable from JavaScript. This is why
3.1 is the top-ranked risk. Current mitigation is that no XSS vector is known —
React escapes everything and there is no HTML injection path.

### "A workspace member tries to read another workspace's data"

They cannot. Four independent barriers: the base queryset join, the create
membership check, `resolve_workspace()` on AI, and the workspace filter inside
`semantic_search`. Cross-tenant requests return 404. This is the part of the
system that would hold up best under review.

### "A malicious document tries prompt injection"

Content is fenced in `<source>` tags, the system prompt states that CONTEXT is
data and never instructions, and the user's real question comes last. Not a
guarantee — prompt injection is unsolved — but the containment is: retrieval is
workspace-scoped, and the model has **no tools**, so even a successful injection
cannot read another tenant or write anything.

### "Someone floods the login endpoint"

10 attempts/minute per IP. Distributed across many IPs it would still get
through, and nothing locks the account or alerts. Rate limiting is the only
control.

---

## Part 5 — Prioritised fix list

| # | Fix | Severity | Effort |
|---|---|---|---|
| 1 | Move the refresh token to an httpOnly, Secure, SameSite cookie set by the backend; keep the access token in memory | 🔴 | High — changes the auth flow and removes the need for `proxy.ts` to read cookies |
| 2 | Add `; Secure` to cookies when the page is HTTPS | 🔴 | Trivial |
| 3 | File size + extension validation on upload; serve with `Content-Disposition: attachment` | 🟠 | Low |
| 4 | Extend the `proxy.ts` matcher to every authenticated route | 🟠 | Trivial |
| 5 | Return 404 for both branches in `resolve_workspace` | 🟠 | Trivial |
| 6 | Add a Content-Security-Policy header | 🟡 | Low |
| 7 | Schedule `flushexpiredtokens` (Celery beat) | 🟡 | Low |
| 8 | Configure `LOGGING` + an error tracker | 🟡 | Low |
| 9 | Email verification on registration | 🟡 | Medium |
| 10 | Change `Comment.author` to `SET_NULL`; add a user-deletion strategy for owned workspaces | 🟡 | Medium (migration) |

---

**Next:** [19 — Performance & Scalability](19-performance-scalability.md)
