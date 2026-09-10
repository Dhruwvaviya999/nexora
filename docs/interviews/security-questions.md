# Interview — Security Questions (20)

[← Interviews index](README.md) · [Full review](../18-security.md)

The rule for this section: **never claim something is secure because a library is
present.** Point at the code that enforces it, and name the gap.

---

**1. How do you prevent one customer from seeing another's data?**
Four independent barriers.
`WorkspaceScopedViewSet.get_queryset()` filters through the membership table, so
another tenant's row is never in the queryset — reads return **404, not 403**.
`perform_create` checks membership explicitly, because `get_queryset` does not
protect creates. `resolve_workspace()` gates every AI endpoint before any
retrieval. And `semantic_search()` filters `workspace=` before the vector
ordering, so retrieval physically cannot cross tenants.

**2. Why 404 rather than 403?**
403 would confirm the id exists somewhere. 404 does not. It falls out of filtering
the queryset rather than checking permission on a fetched object.

**3. How are passwords stored?**
Django's default PBKDF2, applied through `set_password()` in
`UserManager._create_user` and in `PasswordResetConfirmSerializer.save`. There is
no custom `PASSWORD_HASHERS` in base or production — the MD5 override in
`test.py` applies only to the test database, for suite speed.

**4. What password rules do you enforce?**
Django's four validators — user-attribute similarity, minimum length, common
password list, numeric-only — and they actually run, because both password fields
declare `validators=[validate_password]`. The frontend zod schema mirrors 8-128
characters for UX only.

**5. Where are your JWTs stored, and what is the risk?**
Cookies, `nexora.accessToken` and `nexora.refreshToken` — set by JavaScript, so
**not httpOnly**. Any XSS on the frontend origin can read both, and the refresh
token is valid for 7 days.
It is a deliberate trade-off, documented in `token-storage.ts` itself: cookies so
the Next.js edge proxy can read them server-side. It is the top-ranked risk in my
own security review.

**6. How would you fix it?**
Have the backend set an httpOnly, Secure, SameSite refresh cookie on login, keep
the access token in memory only, and add a refresh endpoint that reads the cookie.
That also removes the reason `proxy.ts` needed to read tokens at all. In the
meantime, appending `; Secure` when the page is HTTPS is a one-line improvement.

**7. What mitigates the XSS risk today?**
React escapes by default, and there is **no `dangerouslySetInnerHTML` anywhere in
the frontend** — I verified that. There is no user-supplied HTML rendering path.
So there is no known XSS vector; the exposure is what would happen if one
appeared. A Content-Security-Policy would reduce the impact, and there isn't one.

**8. Are you vulnerable to SQL injection?**
No. There is zero raw SQL — no `.raw()`, no `cursor.execute` outside
`connection.ensure_connection()` in the health check. Every query is ORM-built and
parameterised, including the pgvector `CosineDistance` annotation.

**9. What about CSRF?**
Structurally not applicable to the API: it authenticates with a **header**, not a
cookie, and a cross-site request cannot forge an `Authorization` header.
`CsrfViewMiddleware` is enabled and does real work only for the Django admin.
Tokens *are* in cookies on the frontend origin, mitigated by `SameSite=Lax` and by
the API ignoring cookies entirely.

**10. Describe your rate limiting.**
Six scopes. `login` 10/min, `register` 5/hour, `password_reset` 5/hour — all
keyed by **IP, not user**, because the point is to limit an attacker with no
account who would otherwise get a fresh bucket per guessed email. `ai` is 30/hour
per user because LLM calls cost money. Plus 60/min anonymous and 1000/hour
authenticated globally.
Counters live in Redis in production — with a per-process LocMem cache the
effective limit becomes `rate × worker_count`.

**11. Why doesn't password reset throttle by email address?**
That would let an attacker lock a specific person out of resets by burning their
quota. The class comment states exactly that.

**12. Can someone enumerate your users?**
Not through password reset — it returns the same 202 and body whether or not the
account exists, and the docstring says why. Registration does reveal existence
("A user with this email already exists"), which is hard to avoid on a
registration form and is limited to 5 attempts per hour.
One inconsistency: `resolve_workspace` returns 404 for a missing workspace and
403 for one you are not in, so **workspace** existence is probeable.

**13. What happens if an attacker steals a refresh token?**
They get access until the real user's next refresh. Rotation plus
`BLACKLIST_AFTER_ROTATION` make the token single-use, so the two sessions
invalidate each other — turning silent compromise into a visible session death.
Nothing detects or alerts on that. The user can kill it by resetting their
password, which revokes **every** outstanding refresh token. There is no "sign out
everywhere" button.

**14. Why does password reset revoke all sessions?**
Because refresh tokens outlive the reset by days, so whoever prompted the reset
would keep access. `_blacklist_all_refresh_tokens()` blacklists every
`OutstandingToken` for the user. Resetting because you think you were compromised
now actually kicks the attacker out.

**15. How is the websocket secured?**
Three layers. `OriginValidator` checks the Origin against
`CORS_ALLOWED_ORIGINS`, and refuses a missing Origin. `JWTAuthMiddleware`
validates the token from the query string. The consumer closes with 4401 if the
user is anonymous — deliberately refusing rather than accept-then-close, which
would look like success. Each connection joins a group private to one user id.

**16. The token is in the URL. Isn't that bad?**
It is a known trade — the browser WebSocket API cannot set headers, and this is
the standard workaround. The mitigations are documented in the file: wss in
production, and a 15-minute token lifetime. The residual risk is a reverse proxy
logging query strings, which I would need to configure against.

**17. What is your file upload security posture?**
Weak, honestly. Authentication and workspace scoping are enforced, and the stored
path is partitioned by workspace. But there is **no size limit, no MIME
whitelist and no content validation** — only text *extraction* is restricted by
extension. In DEBUG mode an uploaded HTML or SVG file becomes a fetchable URL on
the API origin, which is a stored-XSS vector against that origin. The fix is a
`validate_file` on the serializer plus `Content-Disposition: attachment` on serve.

**18. How do you protect against prompt injection?**
Three mechanisms plus ordering. `sanitize_input` strips control characters and
caps length at 4000. `wrap_untrusted` fences retrieved content in pseudo-XML.
`SYSTEM_GUARDRAILS` states at the highest priority that CONTEXT is untrusted data
and never instructions. And the user's real question comes **last**, so recency
bias favours it.
The honest limit: prompt injection is not solved. The containment is that
retrieval is workspace-scoped and **the model has no tools** — even a successful
injection cannot reach another tenant or write anything. Generated tasks are
returned for human review, never persisted by the model.

**19. Where are your secrets, and are any committed?**
All from environment variables via django-environ. `.gitignore` covers `.env`,
`backend/.env` and `frontend/.env`, and I verified with `git ls-files` that no
real `.env` is tracked — only `.env.docker.example` and `backend/.env.example`,
which contain placeholders only. `SECRET_KEY` has no default, so an empty one
fails Django's checks, and compose refuses to start without it.
Per-workspace AI API keys are Fernet-encrypted at rest, and the model exposes only
`has_api_key` — never the plaintext.

**20. What are the three biggest security gaps, and how would you fix them?**

1. **Non-httpOnly tokens.** Backend-set httpOnly refresh cookie, access token in
   memory.
2. **No upload restrictions.** Size and extension validation, plus
   `Content-Disposition: attachment` and a real object store rather than serving
   from the API origin.
3. **No security observability.** No `LOGGING` config, no error tracker, no
   record of failed logins or permission denials. There is no way to answer "was
   this account under attack last Tuesday?"

Runners-up: the edge guard covers only 2 of 12 protected route trees; no
Content-Security-Policy; no email verification; the JWT blacklist is never pruned
because there is no scheduler at all.

---

## The three sentences that land best

> "Tenant isolation is enforced in four independent places, and cross-tenant
> reads return 404 rather than 403 so the API never confirms an id exists."

> "The tokens aren't httpOnly — that was a deliberate trade for the edge guard,
> documented in the file. The correct fix is a backend-set httpOnly refresh
> cookie, which also removes the reason the edge guard needed them."

> "The AI has no tools. Retrieval is workspace-scoped, retrieved content is fenced
> as untrusted, and generated tasks go through the normal Task API for human
> review — so even a successful prompt injection can't read another tenant or
> write anything."

---

**Next:** [Scenario questions](scenario-questions.md)
