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
- `CORS_ALLOW_CREDENTIALS = True` — required so the browser sends the httpOnly
  refresh cookie to the auth endpoints. Safe because the allowed origins are an
  explicit list, never a wildcard.
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

**Since the httpOnly change**, the API *does* accept a cookie — the refresh
token — on two endpoints. Those are protected by `SameSite=Lax`, which stops a
cross-site POST from carrying it, and by the token being path-scoped to
`/api/v1/auth/`. Every other endpoint still authenticates by header only, so the
CSRF surface is limited to refresh and logout, neither of which is
state-changing in a way an attacker benefits from (the worst case is logging
someone out).

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

### ✅ 3.1 Tokens readable by JavaScript — **FIXED**

**Was:** both tokens were written to non-httpOnly cookies by page script, so any
XSS could exfiltrate a 7-day refresh token.

**Now:** the refresh token is issued by the backend as an **httpOnly** cookie and
never enters JavaScript at all; the access token is held in a module-scoped
variable (memory only) and dies with the tab.

| Piece | File |
|---|---|
| Cookie helpers (set / clear / read) | `backend/apps/accounts/cookies.py` |
| Login strips `refresh` from the body into the cookie | `LoginView.post` |
| Cookie-based refresh, rotated token never in the body | `CookieTokenRefreshView` |
| Logout blacklists from the cookie and clears it | `LogoutView.post` |
| Password-reset confirm also clears it | `PasswordResetConfirmView.post` |
| Access token in memory; no token in any cookie | `frontend/src/lib/auth/token-storage.ts` |

**The cross-origin problem, and how it is solved.** `proxy.ts` runs at the edge
on the frontend origin and cannot read a cookie scoped to the API origin. It no
longer needs to: it reads `nexora.session`, a marker cookie whose value is the
literal string `"1"` and which contains **no credential**. Forging it gains
nothing — the page renders, every API call 401s, and the layout redirects.

**Residual risk:** an XSS can still read the in-memory access token for up to 15
minutes. That is inherent to any browser client and is a very different blast
radius from a week-long refresh token.

**Tests:** `apps/accounts/tests.py::RefreshCookieTests` (11 tests) pins the whole
contract — no `refresh` in the login body, httpOnly/SameSite/Max-Age flags,
refresh from cookie with an empty body, rotation invalidating the previous
token, logout and reset clearing it, and the non-browser body fallback.
`frontend/src/lib/auth/token-storage.test.ts` asserts the negative space: no
token is ever written anywhere script can read at rest.

### ✅ 3.2 `Secure` flag not set on token cookies — **FIXED**

The refresh cookie takes `secure` from `AUTH_COOKIE_SECURE` (set `True` on any
HTTPS deployment; the env templates say so). The session marker adds `; Secure`
automatically whenever `location.protocol === "https:"`.

`AUTH_COOKIE_SAMESITE` is configurable and defaults to `Lax`, which is correct
whenever the frontend and API share a site — `localhost:3000` → `localhost:8000`
and `app.example.com` → `api.example.com` both qualify. A genuinely cross-site
split needs `None` **and** `Secure`, which the comments call out.

`CORS_ALLOW_CREDENTIALS = True` is now required and set, and is safe because
`CORS_ALLOWED_ORIGINS` is an explicit list — browsers forbid credentials with a
wildcard origin anyway.

### ✅ 3.3 No file upload restrictions — **FIXED**

Three layers now:

1. **Size** — `MAX_UPLOAD_SIZE` (25 MB default) checked in
   `DocumentSerializer.validate_file`, so the user gets a field error rather
   than a raw 413. `DATA_UPLOAD_MAX_MEMORY_SIZE` is derived from it so an
   oversized body is refused before being buffered.
2. **Type** — an extension allow-list (`ALLOWED_UPLOAD_EXTENSIONS`). `.html`,
   `.svg` and `.exe` are rejected outright.
3. **Serving** — files are no longer reachable at a public `/media/` URL at all
   (see 3.3b), and the download view forces
   `Content-Disposition: attachment` plus `X-Content-Type-Options: nosniff`.

**Tests:** `apps/documents/tests.py` covers oversized, `.html`, `.exe`, and an
allowed non-text type, asserting the *specific* rejection reason so the tests
cannot pass for the wrong reason.

### ✅ 3.3b Uploads were publicly readable — **FIXED (new finding)**

Raising 3.3 surfaced a worse problem that was not in the original list:
`file_url` pointed at `MEDIA_URL`, an **unauthenticated** path. Anyone holding
or guessing it could read another workspace's document, bypassing every
permission check in the project.

Uploads are now streamed by `GET /documents/{id}/download/`, which goes through
`get_object()` and therefore the normal membership filter. `file_url` points
there. Tenancy is tested: an outsider gets 404, anonymous gets 401.

### ✅ 3.4 Edge guard did not cover most protected routes — **FIXED**

The matcher now covers all twelve authenticated route trees — `/dashboard`,
`/workspaces`, `/projects`, `/tasks`, `/handovers`, `/documents`, `/ai`,
`/activity`, `/search`, `/settings`, `/notifications`, `/invitations` — so a
logged-out visitor is redirected at the edge instead of seeing a shell flash.
Password-reset pages remain deliberately excluded from the auth-page bounce.

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

### ✅ 3.7 Blacklisted tokens never pruned — **FIXED**

A `CELERY_BEAT_SCHEDULE` now exists (there was no scheduler at all), with a
`beat` service in `docker-compose.yml`. Four nightly maintenance tasks in
`apps/common/tasks.py`:

| Task | Does |
|---|---|
| `common.flush_expired_tokens` | Runs SimpleJWT's `flushexpiredtokens` — the important one, since the table gains a row per refresh and is read on every token validation |
| `common.expire_stale_invitations` | Flips past-due pending invites to `expired`, so counts stop drifting |
| `common.prune_embedding_jobs` | Drops finished jobs older than 30 days, leaving unfinished ones visible |
| `common.prune_search_history` | Drops raw query text older than 90 days — a privacy window as much as a storage one |

All four are idempotent, so a duplicated beat tick is harmless. Exactly **one**
beat process must run per deployment; the compose comment says so.

**Tests:** `apps/common/tests.py::MaintenanceTaskTests`, including one that
asserts every task name in the schedule actually resolves in the Celery registry
— a typo there would otherwise fail silently at 3am.

### 🟡 3.8 No security headers beyond Django's defaults

No Content-Security-Policy, no `Referrer-Policy`, no `Permissions-Policy` — on
either the Django side or in `next.config.ts` (which is an empty config object).

A CSP would reduce the residual XSS impact described in 3.1.

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

## Part 5 — Fix status

### Fixed in this pass

| # | Item | What changed |
|---|---|---|
| 1 | httpOnly refresh cookie | Backend issues it; access token is memory-only; edge guard reads a value-less marker instead |
| 2 | `Secure` / `SameSite` on cookies | Both configurable, documented, and applied automatically on HTTPS |
| 3 | Upload size + type limits | `validate_file` with a 25 MB cap and an extension allow-list |
| 3b | **Public media URLs** (new finding) | Replaced with an authenticated, workspace-scoped download endpoint |
| 4 | Edge guard coverage | All twelve protected route trees now matched |
| 7 | Unbounded token table | Celery beat schedule + `beat` service + four pruning tasks |

### Still open

| # | Item | Severity | Fix |
|---|---|---|---|
| 3.5 | AI endpoints leak workspace existence (404 vs 403) | 🟠 | Raise `NotFound` in both branches of `resolve_workspace` |
| 3.6 | No account lockout, MFA or email verification | 🟡 | Verification email on register; lockout after N failures |
| 3.8 | No Content-Security-Policy | 🟡 | Add CSP headers; reduces the residual XSS impact in 3.1 |
| 3.9 | No security observability | 🟡 | `LOGGING` config + an error tracker; record failed logins and permission denials |
| 3.10 | `Comment.author` / `Workspace.owner` cascade on user delete | 🟡 | `SET_NULL` for comments; block or force transfer for owned workspaces |
| 3.11 | Fernet key derived from `SECRET_KEY` when unset | 🟢 | Set a dedicated `AI_FIELD_ENCRYPTION_KEY` in production |

The highest-value remaining item is **3.9** — without logging, none of the
controls above can be observed failing.
