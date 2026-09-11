# Interview — Frontend Questions (20)

[← Interviews index](README.md)

---

**1. Why Next.js App Router rather than Vite + React Router?**
Two things I actually use: `src/proxy.ts` — an edge guard that runs before a page
renders, which client-side routing cannot do — and route groups, so `(auth)` and
`(app)` get different layouts with no URL impact.
Honest caveat: every `(app)` page is `"use client"`, so I am not currently
benefiting from server components for data. I use the App Router for routing and
middleware, not RSC data fetching.

**2. Walk me through the startup sequence.**
`src/proxy.ts` at the edge → `app/layout.tsx` (server: html, fonts, metadata) →
`app/providers.tsx` (client: QueryClient → Theme → Auth) → `app/(app)/layout.tsx`
(the real auth gate + sidebar + WorkspaceProvider) → the page.
Three sequential round trips follow: `/auth/me/` → `/workspaces/` →
`/dashboard/?workspace=`.

**3. That's three sequential requests before the dashboard renders. Would you fix
it?**
Yes. Each waits on the last because the workspace id is not known until step 2
returns. Either persist the last workspace id in a cookie so the dashboard fetch
starts in parallel with `/auth/me/`, or add a single `/auth/bootstrap/` endpoint
returning user + workspaces + dashboard.

**4. How does `getQueryClient()` work and why?**
On the server it makes a fresh client per request, so server-rendered data is
never shared between users. In the browser it returns a module-level singleton,
so React re-renders do not blow away the cache. It is the recommended TanStack
Query + App Router pattern.

**5. Explain your query key strategy.**
Each hook file owns a `KEYS` object: `["tasks"]`, `["tasks","list",params]`,
`["tasks", id]`. Params are part of the key, so a different filter or page is a
different cache entry — previously loaded pages stay warm. Mutations invalidate by
prefix.

**6. What happens to the cache when you switch workspace?**
`workspace` is a param on nearly every list key, so switching changes ~12 keys at
once and every visible list refetches automatically. No manual invalidation. The
previous workspace's data stays cached under its own keys, so switching back is
instant.

**7. Why did you write your own fetch wrapper instead of using Axios?**
The behaviour I needed — single-flight refresh with a one-shot retry — is custom
either way. Axios would give me interceptors, but I would still write the refresh
logic. The wrapper is 142 lines and does JWT injection, refresh, FormData
detection and error normalisation. Adding a dependency would not remove code.

**8. Explain the single-flight refresh.**
`refreshPromise` is module scope. The first 401 creates it; every other
concurrent 401 awaits the same promise. `.finally()` clears the slot. It matters
because refresh tokens rotate and are single-use — parallel refreshes would
blacklist each other and log the user out.

**9. How do server validation errors reach the right form field?**
`applyFieldErrors()` in `lib/api/errors.ts` maps DRF's `{field: ["msg"]}` shape
onto react-hook-form's `setError`. So a backend rule like "User is not a member of
this workspace" renders inline under the assignee field, not just in a toast.
Both run — inline **and** a toast — so nothing is missed if the field is
scrolled off screen.

**10. Why zod on the client if the server validates anyway?**
UX only. It gives feedback without a round trip. Client validation is never the
security boundary — the server re-validates everything, and
`lib/validations/auth.ts` deliberately mirrors the backend rules.

**11. Why only two React Contexts?**
Because almost nothing here is genuinely shared mutable client state. It is nearly
all server state, which belongs in a cache with invalidation rules. The two things
that *are* client-owned — who am I, and which workspace am I in — are exactly the
two contexts.

**12. Explain `WorkspaceProvider`'s resolution logic.**
`selectedId ?? storedId ?? workspaces[0] ?? null`, resolved **during render**.
`selectedId` is the in-tab explicit choice; `storedId` comes from `localStorage`
through `useSyncExternalStore`, which picks up other tabs. Both are needed because
a same-tab `setItem` fires no `storage` event. Resolving during render rather than
in effects eliminates a race the previous version had — the comment in the file
records that bug.

**13. Where is form state kept?**
In react-hook-form's ref-based store, not `useState`. That is why typing does not
re-render the page. Server errors are pushed into the same store, so both
validation sources render through one mechanism.

**14. How does file upload work on the client?**
`components/shared/file-upload.tsx` is a controlled picker — it calls no API and
just hands a `File` to its parent. The page builds a `FormData`, and
`client.ts` detects it and **omits `Content-Type`** so the browser can set the
multipart boundary. Setting it manually would break the upload.

**15. How does the websocket integrate with TanStack Query?**
`use-notification-socket.ts` manages the connection; on a message it calls
`invalidateQueries(["notifications"])` and ignores the payload. The socket is a
signal, not data — so there is one source of truth and no chance of the cache
drifting from what the server would return.

**16. What happens when the socket cannot connect?**
Exponential backoff `1s → 2s → 5s → 10s → 30s`. Close code 4401 (unauthenticated)
retries at the *slowest* interval rather than hammering the server with
credentials it already refused. Close 1000 does not reconnect. And
`useUnreadCount` polls every 30 seconds while the socket is down. The user never
sees an error.

**17. How is role-based UI handled?**
`activeWorkspace.role` comes from the workspace serializer, computed per request.
`app-sidebar.tsx` appends the Reviews nav item only for `REVIEWER_ROLES`, and the
handover detail page gates the review card the same way. **This is convenience,
not security** — the server re-checks independently, and typing the URL still
renders the page.

**18. What is your loading and error state story?**
Loading is good: page spinners, `Skeleton` grids matching the final layout, a
table skeleton, and `EmptyState`/`NoWorkspace` components.
Errors are handled too, now: eight pages branch on `isError` before the loading
guard and render a shared `<ErrorState/>` whose heading is derived from the
`ApiError.status` (a 403 reads "You don't have access to this"), with a retry
wired to `refetch()`. Three error boundaries catch render-time exceptions —
`app/(app)/error.tsx` keeps the sidebar intact, `app/error.tsx` covers public
routes, and `app/global-error.tsx` handles a root-layout failure.

**19. Why is `PAGE_SIZE = 20` duplicated in `lib/constants.ts`?**
It mirrors DRF's `PAGE_SIZE`. It is duplication I would rather not have — along
with the 7-day cookie `MAX_AGE` mirroring `JWT_REFRESH_TOKEN_LIFETIME_DAYS`.
Both are silent desync risks. Ideally the API would expose them, or the types
would be generated from the OpenAPI schema.

**20. What would you improve on the frontend?**
Error boundaries and `isError` branches. Put list filters in the URL so views are
shareable. Generate `src/types/` from the OpenAPI schema rather than
hand-mirroring serializers. Test `lib/api/client.ts` — it is the most logic-dense
file and has no tests, while the four files that *are* tested are among the
simplest.

---

**Next:** [Backend questions](backend-questions.md)
