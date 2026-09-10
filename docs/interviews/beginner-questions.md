# Interview — Beginner Questions (30)

[← Interviews index](README.md)

Try to answer before reading the model answer.

---

**1. What is Nexora, in one sentence?**
A multi-tenant team workspace for projects, tasks and documents, with formal
manager-reviewed task handovers and an AI assistant that answers questions over
the workspace's own documents.

**2. What is the frontend built with?**
Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS 4, shadcn/ui
components, TanStack Query for server state, react-hook-form + zod for forms.

**3. What is the backend built with?**
Django 5.1 with Django REST Framework. Plus SimpleJWT for auth, django-filter,
drf-spectacular, Channels for websockets and Celery for background jobs.

**4. Which database, and why that one?**
PostgreSQL 16 with the pgvector extension. pgvector is the reason — it lets
embedding vectors live in the same database as everything else, so there is no
separate vector store to sync, back up or secure.

**5. Do you use Axios?**
No. `frontend/src/lib/api/client.ts` is a hand-written wrapper around the native
`fetch` — about 140 lines that handle JWT injection, token refresh, FormData and
error normalisation.

**6. What is a "workspace"?**
The tenant boundary. Every project, task, document, comment and notification
belongs to one. A person can belong to several workspaces with a different role
in each.

**7. What are the four roles?**
Owner, admin, manager, member. Stored on `workspaces_workspacemember.role`.

**8. What can a manager do that a member cannot?**
Review handovers — approve or reject them. That is the only difference.

**9. Which file runs first when the frontend starts?**
For a matched route, `src/proxy.ts` runs at the edge before anything renders.
Then `app/layout.tsx`, then `app/providers.tsx`, then the route group's layout,
then the page.

**10. What is `src/proxy.ts`?**
The Next.js edge route guard — in Next.js 16 this file used to be called
`middleware.ts`. It checks whether an auth cookie is *present* and redirects.
It does not verify the token.

**11. What do the parentheses in `app/(app)/` mean?**
It is a route group. The parentheses do not appear in the URL; they exist so the
authenticated pages and the auth pages can have different `layout.tsx` files.

**12. How does the frontend know which page to show?**
Next.js App Router maps the filesystem to URLs. `app/(app)/tasks/[id]/page.tsx`
serves `/tasks/<uuid>`.

**13. Where do API URLs live?**
`frontend/src/lib/constants.ts`, in the `API_ROUTES` object. Nothing hard-codes a
path.

**14. How does the frontend send the token?**
`lib/api/client.ts` reads it from a cookie and sets the header
`Authorization: Bearer <access token>` on every request.

**15. Where are tokens stored?**
In cookies — `nexora.accessToken` and `nexora.refreshToken`. Cookies rather than
localStorage so the Next.js edge proxy can read them server-side.

**16. What is TanStack Query for?**
Server state. It caches API responses, dedupes requests, and handles refetching
and invalidation — so no server data is kept in `useState` anywhere in this app.

**17. How many React Contexts are there?**
Two. `AuthProvider` (who am I) and `WorkspaceProvider` (which workspace am I
looking at).

**18. Why no Redux?**
Almost nothing in this app is shared mutable *client* state. It is nearly all
server state, which belongs in a cache with invalidation rules rather than a
store you keep in sync by hand.

**19. What is a DRF ViewSet?**
A class that bundles the standard CRUD actions for a resource. Registering it
with a router generates `/tasks/`, `/tasks/{id}/` and any custom actions
automatically.

**20. What is a serializer?**
DRF's translation and validation layer — it converts JSON into validated model
data on the way in, and model instances into JSON on the way out.

**21. What is the base URL of the API?**
`/api/v1/` — versioned from day one so a `v2` could be mounted alongside it.

**22. What does a list endpoint return?**
DRF's pagination envelope: `{count, next, previous, results}`, 20 per page.

**23. How is the "active workspace" remembered between visits?**
`localStorage` under `nexora.activeWorkspace`, read by `WorkspaceProvider`.

**24. What happens when you switch workspace?**
The workspace id is part of every query key, so every list query key changes and
every visible list refetches automatically. No manual invalidation.

**25. What is Celery used for here?**
Two things: embedding uploaded documents, and sending outgoing email. Both are
too slow to hold a web request open.

**26. What are websockets used for?**
Pushing notifications. The socket only signals that something changed; the client
then refetches over REST.

**27. What happens if the websocket does not connect?**
The unread count polls every 30 seconds instead. The feature degrades rather than
disappearing.

**28. What are Django signals used for in this project?**
Four things: writing the audit log, syncing @mentions from comment text, creating
notifications, and kicking off document embedding.

**29. How do you run the whole project?**
`docker compose up --build` after copying `.env.docker.example` to `.env` and
setting a `SECRET_KEY`. Or natively: PostgreSQL plus `manage.py runserver` and
`pnpm dev`.

**30. What do you need installed to develop locally?**
Only PostgreSQL (with pgvector). Redis, Celery and SMTP are all optional — each
falls back to an in-process equivalent in the development settings.

---

## Rapid fire — answer in five words or less

| Question | Answer |
|---|---|
| Access token lifetime? | 15 minutes |
| Refresh token lifetime? | 7 days |
| Page size? | 20 |
| Embedding dimensions? | 384 |
| Primary key type? | UUID |
| How many application tables? | 19 |
| How many frontend pages? | 37 |
| Which HTTP method for updates? | PATCH |
| Which port is the API on? | 8000 |
| Which port is the frontend on? | 3000 |
| What returns for a cross-tenant read? | 404 |
| What is the only hard dependency? | PostgreSQL |

---

**Next:** [Intermediate questions](intermediate-questions.md)
