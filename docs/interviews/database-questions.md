# Interview — Database Questions (20)

[← Interviews index](README.md)

---

**1. Why PostgreSQL specifically?**
pgvector. There is no equivalent in MySQL, and the whole RAG feature depends on
storing 384-dimension vectors with an HNSW cosine index inside the same database.
`jsonb` and Django's PostgreSQL support are secondary benefits.

**2. Why not a dedicated vector database like Pinecone?**
Because the tenant filter and the vector search become **one query**:
`filter(workspace=ws).annotate(distance=CosineDistance(...))`. With a separate
store I would have to replicate the tenancy model into it, or filter after
retrieval. One database also means one backup, one transaction boundary, and no
sync job. If the corpus grew to hundreds of millions of vectors that calculus
changes.

**3. Walk me through your schema design.**
Nineteen application tables. `accounts_user` for identity; `workspaces_workspace`
and `workspacemember` for tenancy; four content tables (project, task, document,
handover); collaboration (comment, mention, notification); one audit table; two
knowledge tables; five AI tables. Almost every one carries `workspace_id`, a UUID
`id`, timestamps, and usually `created_by`/`updated_by` — all from abstract base
classes.

**4. How does multi-tenancy work at the data layer?**
A `workspace_id` column, not schema-per-tenant or database-per-tenant. Isolation
is enforced by a single queryset filter in `WorkspaceScopedViewSet`, plus an
explicit membership check on create. The trade: cheap operationally, but **the
filter must never be forgotten** — which is exactly why the base class exists, to
make the safe path the default.

**5. Why UUID primary keys?**
Safe to expose in URLs and APIs with no enumeration. Also generated before insert
and collision-free across environments. Costs: 16 bytes versus 4, and random
ordering hurts index locality on insert — which is why everything orders by
`-created_at` rather than by id.

**6. Explain the `WorkspaceMember` table.**
A many-to-many between user and workspace **with extra data** — the role. That is
the classic through-table case: the role belongs to the relationship, not to
either side. It has a unique constraint on `(workspace, user)` and it is the most
read table in the system, since every permission check and every scoped query
joins it.

**7. Walk me through the `on_delete` choices.**
Workspace FKs are all `CASCADE` — deleting a tenant removes its content.
`Task.project` is `CASCADE` because a task cannot exist without its project, but
`Document.project` is `SET_NULL` because a document can be workspace-level.
Every user reference on content is `SET_NULL` — deleting a person must not delete
the work, and the historical record survives.

**8. You said "every user reference" — is that true?**
No, and it is a real inconsistency. `Comment.author` is `CASCADE`, so deleting a
user erases their comments and, via the `parent` cascade, other people's replies
underneath. And `Workspace.owner` is `CASCADE`, so deleting one user destroys
every workspace they own and everything inside it. Both should change —
`SET_NULL` for the comment, and either a block or a forced ownership transfer for
the workspace.

**9. Explain the generic foreign keys.**
`comments_comment` and `activities_activity` both use `content_type` +
`object_id` + `GenericForeignKey`, so one comment table serves projects, tasks and
documents. `object_id` is a `UUIDField` rather than the usual integer, because
every domain model uses UUID keys.
The cost: PostgreSQL cannot enforce that `object_id` points at a live row. On the
comment side an `ALLOWED_TARGETS` whitelist bounds the damage by limiting
`target_type` to three known models.

**10. Why is `object_id` nullable on `activities_activity`?**
Delete rows have no target — the object is gone. That is also why `metadata`
carries a human-readable snapshot: the log still reads correctly after the object
is renamed or deleted.

**11. Walk me through your indexes.**
Fourteen explicit composites beyond the automatic PK and FK ones, and each maps
to a query that exists: `tasks(workspace, status)` for the dashboard counts,
`handovers(workspace, status)` for the reviewer queue,
`comments(content_type, object_id)` for loading a thread,
`notifications(recipient, is_read)` for the unread badge,
`embeddingjob(document, -created_at)` for "latest job", and the HNSW index on the
vector column.

**12. Are any indexes missing?**
Yes — `projects_project(workspace, status, archived)` and
`documents_document(workspace, project)` are both filtered that way with no
composite index. Low impact today because the FK index on `workspace_id` carries
most of the load.

**13. Explain the vector column and its index.**
`VectorField(dimensions=384, null=True)` — nullable so a chunk row can exist
before its embedding is computed. Indexed with HNSW, `vector_cosine_ops`,
`m=16`, `ef_construction=64`. The opclass must match the query operator or the
index is unusable.

**14. HNSW or IVFFlat, and why?**
HNSW. IVFFlat needs a training pass over existing data and degrades as new rows
arrive until re-trained. Documents here arrive one at a time, so incremental
indexing matters more than the lower memory footprint.

**15. Why is `workspace_id` duplicated onto `DocumentChunk`?**
Deliberate denormalisation, and the model docstring says why: so the tenant
boundary is a single indexed filter on similarity queries — the hot path. Without
it, every vector search would join through `documents_document`.

**16. Where do you use transactions, and where should you?**
Four places use them: workspace creation (workspace + owner membership),
ownership transfer (three writes), chunk storage (delete-then-bulk-insert), and
three `on_commit` hooks for ordering with Celery and websockets.
**Missing:** `HandoverViewSet.review` writes the handover and the task with no
transaction. A crash between them leaves an approved handover and an unassigned
task.

**17. What are your JSON columns, and are they indexed?**
Five `jsonb` columns: `task.labels`, `activity.metadata`, `chunk.metadata`,
`aimessage.sources` and `aimessage.metadata`. **None are queried with JSON
operators anywhere**, so no GIN indexes are needed — and that also means
`?labels=bug` is not supported. They are stored and read whole.

**18. Do you have any views, triggers or stored procedures?**
None. All trigger-like behaviour is Django signals, which run in Python in the web
process. The consequence is that a write made outside Django — psql, a data
migration using `bulk_create`, or `queryset.update()` — produces no audit row and
no notification.

**19. What are your N+1 problems?**
The worst is the document serializer: `get_embedding_status` and
`get_chunk_count` each issue one query per row, so a 20-row page is 41 queries.
Three others use `source="...count"` — `member_count`, `task_count`,
`reply_count`. All four convert to `annotate` or a `Prefetch`. Everything else is
covered by `select_related`, which every scoped viewset declares to match its
serializer's nesting.

**20. How would this schema handle a million tasks per workspace?**
The tables are fine — a million rows is small for PostgreSQL, and
`(workspace, status)` covers the common filters. What breaks first is query
*count*, not size: 15+ on the dashboard, 41 on a document list. Then the analytics
8-week window scans, then leading-wildcard `ILIKE` searches. I would collapse the
dashboard counts into aggregates, cache analytics, add `pg_trgm` or full-text
search, and eventually partition `activities_activity` by month since it is
append-only and time-queried.

---

## Schema questions to test yourself

1. Which tables have `workspace_id`, and which of those inherit it versus declare
   it themselves? Why the difference?
2. Which unique constraint is per-tenant, and which is global? Why?
3. Which foreign key would you change first, and to what?
4. What does `related_name="+"` do, and where is it used?
5. Which column is duplicated for performance, and what is the stated reason?

---

**Next:** [Security questions](security-questions.md)
