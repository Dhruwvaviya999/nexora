# Nexora — AI Knowledge & Workflow Assistant

Nexora is a multi-tenant team workspace for managing projects, tasks, documents, and team handovers. Its AI assistant answers questions using knowledge from workspace documents, while role-based permissions keep each workspace's data separated.

## Features

- **Workspaces and access control** — workspace roles, member management, and email invitations.
- **Projects and tasks** — manage work, owners, priorities, statuses, and due dates.
- **Reviewed handovers** — transfer tasks with summaries, pending items, and resources; workspace owners, admins, and managers can review and approve or reject handovers. Export handovers as PDFs.
- **Documents and AI knowledge search** — upload documents, generate embeddings, and ask questions with answers grounded in workspace content and source references.
- **Team collaboration** — threaded comments, @mentions, activity history, and live WebSocket notifications.
- **Analytics and audit trail** — dashboard metrics, workload insights, filters, and CSV activity export.
- **Pluggable AI providers** — Gemini, OpenAI, or Ollama, with document embeddings generated using sentence-transformers and stored in PostgreSQL with pgvector.

## Tech Stack

| Layer | Technologies |
|---|---|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS 4, shadcn/ui, TanStack Query |
| Backend | Django 5.1, Django REST Framework, SimpleJWT |
| Database | PostgreSQL 16, pgvector |
| Background jobs and realtime | Celery, Redis, Django Channels, WebSockets |
| AI | sentence-transformers, Gemini, OpenAI, Ollama |
| Testing and delivery | Django tests, Vitest, Testing Library, Docker Compose, GitHub Actions |

## Run with Docker

**Requirements:** Docker and Docker Compose.

```bash
cp .env.docker.example .env
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Copy the generated value into `.env` as `SECRET_KEY=...`, then start the application:

```bash
docker compose up --build
```

Open the frontend at [http://localhost:3000](http://localhost:3000). The API is available at `http://localhost:8000/api/v1`, with interactive API documentation at [http://localhost:8000/api/docs/](http://localhost:8000/api/docs/).

The first Docker build may take longer because the backend installs AI and document-processing dependencies. Document embedding and asynchronous jobs run through the worker service.

## Tests and checks

Run backend tests:

```bash
cd backend
python manage.py test
```

Run frontend checks:

```bash
cd frontend
pnpm install
pnpm lint
pnpm typecheck
pnpm test
pnpm build
```

## Repository Structure

```text
nexora/
├── backend/     # Django REST API, domain apps, AI/RAG, and background jobs
├── frontend/    # Next.js application, pages, components, and API client
├── docs/        # Architecture, feature modules, API, testing, and setup docs
├── docker-compose.yml
└── .env.docker.example
```

For deeper implementation details, start with [`docs/README.md`](docs/README.md). API-specific notes are in [`docs/api/README.md`](docs/api/README.md).

## Security Notes

Nexora scopes access to workspace membership and roles. Refresh tokens are delivered in an HTTP-only cookie, while access tokens are held in memory by the frontend. Keep secrets in local environment files, use a unique production `SECRET_KEY`, and never commit credentials.

---

Built with Next.js, Django REST Framework, PostgreSQL, and pgvector.
