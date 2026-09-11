# API — Documents

[← API index](README.md) · [Module deep dive](../modules/documents-knowledge.md)

Base `/api/v1/documents/` · `DocumentViewSet(WorkspaceScopedViewSet)`
· `backend/apps/documents/views.py`

The only endpoint in the API that accepts a file.

```python
parser_classes = (MultiPartParser, FormParser, JSONParser)
```
Multipart for uploads, JSON for metadata-only edits.

---

## `GET /documents/`

**Filters** (`DocumentFilter`): `workspace` · `project` · `file_type`
(`exact`, `icontains`)
**Search:** `title`, `description`
**Ordering:** `created_at`, `updated_at`, `title`, `file_size`

**Response** — paginated `DocumentSerializer`:

```json
{ "id": "<uuid>", "workspace": "<uuid>", "project": "<uuid>|null",
  "title": "Q3 runbook.pdf", "description": "",
  "file_url": "http://localhost:8000/api/v1/documents/<uuid>/download/",
  "file_type": "application/pdf", "file_size": 284913,
  "embedding_status": "completed", "chunk_count": 37,
  "uploaded_by": { ...UserSerializer... },
  "created_by": { ... }, "updated_by": { ... },
  "created_at": "...", "updated_at": "..." }
```

`file` itself is **write-only** (`extra_kwargs = {"file": {"write_only": True,
"required": False}}`); the response exposes `file_url` instead:

```python
def get_file_url(self, obj):
    if not obj.file: return None
    request = self.context.get("request")
    path = reverse("v1:documents:document-download", kwargs={"pk": obj.pk})
    return request.build_absolute_uri(path) if request else path
```

`file_url` points at the **authenticated download endpoint**, never a raw
`/media/` path. A public media URL would be an unauthenticated cross-tenant read
*and* would 404 in production, where Django does not serve `/media/`.

### The two expensive fields

```python
def get_embedding_status(self, obj):
    job = obj.embedding_jobs.order_by("-created_at").first()    # 1 query per row
    return job.status if job else None

def get_chunk_count(self, obj):
    return obj.chunks.count()                                    # 1 query per row
```

**Two extra queries per document.** A 20-row page is 41 queries. This is the
worst N+1 in the codebase — fix in
[19-performance-scalability.md](../19-performance-scalability.md#-21-n1-on-the-document-list).

`embedding_status` values: `null` (never processed) · `pending` · `processing` ·
`completed` · `failed`. Rendered by
`components/ai/embedding-status-badge.tsx`.

---

## `POST /documents/` — multipart upload

**Content-Type:** `multipart/form-data`

**Form fields**

| Field | Required | Notes |
|---|---|---|
| `workspace` | ✅ | UUID; membership-checked |
| `file` | ✅ | The binary |
| `project` | — | UUID, optional |
| `title` | — | Defaults to the filename |
| `description` | — | |

**Client side** — the form builds the `FormData` itself and `apiClient` detects
it:

```ts
const form = new FormData();
form.append("workspace", activeWorkspaceId);
form.append("file", values.file);
if (values.project)     form.append("project", values.project);
if (values.title)       form.append("title", values.title);
if (values.description) form.append("description", values.description);
await uploadDocument.mutateAsync(form);
```
`app/(app)/documents/new/page.tsx:30-38`

```ts
const isFormData = typeof FormData !== "undefined" && body instanceof FormData;
const baseHeaders = isFormData ? {} : { "Content-Type": "application/json" };
```
`lib/api/client.ts:85-88` — **the header is deliberately omitted** so the browser
generates the multipart boundary. Setting it manually would break the upload.

**Server side** — `DocumentSerializer.create`:

```python
upload = validated_data.get("file")
validated_data["file_size"] = upload.size
validated_data["file_type"] = getattr(upload, "content_type", "") or os.path.splitext(upload.name)[1].lstrip(".")
validated_data["uploaded_by"] = request.user
if not validated_data.get("title"):
    validated_data["title"] = os.path.basename(upload.name)
```

**Validation**

| Check | Failure |
|---|---|
| `file` present on create | `400 {"file": ["A file is required."]}` |
| Workspace membership | `403` from `_require_membership` |

**Upload validation** (`DocumentSerializer.validate_file`):

| Check | Failure |
|---|---|
| Size ≤ `MAX_UPLOAD_SIZE` (25 MB default) | `400 {"file": ["File is too large (31.2 MB). The limit is 25 MB."]}` |
| Extension in `ALLOWED_UPLOAD_EXTENSIONS` | `400 {"file": ["Unsupported file type '.html'. Allowed: ..."]}` |

Allowed: `.pdf .docx .txt .md .markdown` (text-extractable, these feed the RAG
pipeline) plus `.csv .xlsx .pptx .png .jpg .jpeg .gif .webp` (stored, not
embedded). `.html`, `.svg` and `.exe` are rejected — an HTML file served back
from the API origin would be a stored-XSS vector.

`DATA_UPLOAD_MAX_MEMORY_SIZE` is derived from `MAX_UPLOAD_SIZE`, so an
oversized body is refused before being fully buffered.

**Storage:** `document_upload_path` → `documents/<workspace_id>/<filename>` under
`MEDIA_ROOT`. In Docker that is a named volume shared with the worker.

**Response `201`** — returned **immediately**; embedding continues in the
background.

**Side effects**
1. `activities_activity` row `document.created`
2. `post_save` → `knowledge/handlers.py::_on_document_created`
3. If the extension is supported → `EmbeddingJob` (pending) +
   `process_document_task.delay()` after commit
4. If unsupported (e.g. `.png`) → **skipped silently**, `embedding_status` stays
   `null`

Full pipeline: [11-data-flow.md](../11-data-flow.md#flow-4--uploading-a-document-through-to-a-searchable-vector).

---

## `PATCH /documents/{id}/` — metadata only

```python
def validate(self, attrs):
    # File is required on create, optional on update (metadata-only edits).
    if self.instance is None and not attrs.get("file"):
        raise serializers.ValidationError({"file": "A file is required."})
    return attrs
```

Editable: `title`, `description`, `project`.

**Important:** editing metadata does **not** re-embed, because the signal fires
only on `created`. Replacing the file also does not re-embed — use `reindex`.

---

## `GET /documents/{id}/download/`

**The only way to read an uploaded file.**

| | |
|---|---|
| **Auth** | member — `get_object()` applies the workspace-membership filter, so a non-member gets **404** |
| **Response** | `200` with the file streamed via `FileResponse` |
| **Headers** | `Content-Disposition: attachment; filename="..."`, `X-Content-Type-Options: nosniff`, `Content-Length` |

Why a view rather than a static path, from the docstring:

1. **Tenancy.** A raw media path is an unauthenticated read — anyone holding or
   guessing the URL could fetch another workspace's file, bypassing every
   permission check in the project.
2. **Deployment.** `django.conf.urls.static` only serves media while `DEBUG` is
   on. A view works identically with `DEBUG=False` and with S3.

Always an attachment: an uploaded `.html` or `.svg` served inline would execute
on the API's origin. The content type is guessed from the **extension**, not
from the stored `file_type`, which is client-supplied and untrustworthy. The
filename is stripped of quotes and newlines so a crafted title cannot inject
response headers.

`404` if the document has no file, or if the row exists but the stored file is
missing.

**Client side** — must be fetched with the bearer token, so a plain `<a href>`
will not work:

```ts
await downloadFile(API_ROUTES.documents.download(doc.id), doc.title);
```

`lib/api/download.ts` obtains an access token up front (minting one from the
refresh cookie after a reload), retries once on a 401, reads the blob and
triggers the browser download.

---

## `DELETE /documents/{id}/`

`204`. Cascades to `knowledge_documentchunk` and `knowledge_embeddingjob`.

**The file on disk is not deleted.** Django's `FileField` does not remove the
underlying file on model delete, and nothing in this codebase does it manually.
*Confirmed by absence — there is no `post_delete` handler on `Document` touching
storage.*

---

## `POST /documents/{id}/reindex/`

```python
@action(detail=True, methods=["post"])
def reindex(self, request, pk=None):
    from apps.knowledge.services.processor import enqueue_document   # local import
    document = self.get_object()
    job = enqueue_document(document)
    return Response({"document": str(document.id), "status": job.status,
                     "chunk_count": job.chunk_count, "error": job.error}, status=202)
```

**Auth:** member. **No body.**

**Response `202 Accepted`**
```json
{ "document": "<uuid>", "status": "pending", "chunk_count": 0, "error": "" }
```

202, not 200 — the work has been *accepted*, not completed. The client polls the
document's `embedding_status` to see progress.

The local import keeps `apps.documents` importable without the AI stack.

**What re-indexing does:** creates a fresh `EmbeddingJob`, then on the worker
re-extracts, re-chunks, re-embeds, and **atomically** deletes and replaces all
chunks (`_store_chunks` is `@transaction.atomic`), so the document is never left
with zero chunks.

There is also a management command for bulk work:
`python manage.py reindex_documents`.

---

## Hooks reference

| Hook | Call | Invalidates |
|---|---|---|
| `useDocuments(params)` | `GET /documents/` | — |
| `useDocument(id)` | `GET /documents/{id}/` | — |
| `useUploadDocument()` | `POST /documents/` (FormData) | `["documents"]` |
| `useUpdateDocument(id)` | `PATCH /documents/{id}/` | `["documents"]`, detail |
| `useDeleteDocument()` | `DELETE` | `["documents"]` |
| `useReindexDocument()` | `POST /documents/{id}/reindex/` | `["documents"]`, detail |

---

## Failure reference

| Symptom | Cause |
|---|---|
| `400 {"file": ["A file is required."]}` | Create with no file |
| `embedding_status: null` after upload | Unsupported extension — only `.pdf .docx .txt .md .markdown` are processed |
| `embedding_status: "pending"` forever | No Celery worker consuming, and the broker was reachable enough that the inline fallback did not trigger |
| `embedding_status: "failed"` | Read `EmbeddingJob.error` — it holds the exception text (2000 chars) |
| `chunk_count: 0` with status `completed` | Extraction produced no text — most often a scanned PDF (**no OCR**) |
| `404` on download | Not a workspace member, or the stored file is missing from storage |
| `400 {"file": ["Unsupported file type..."]}` | Extension not in the allow-list |
| `400 {"file": ["File is too large..."]}` | Over `MAX_UPLOAD_SIZE` |
| Upload appears to hang locally | Inline embedding downloading the 90 MB model on first use |
