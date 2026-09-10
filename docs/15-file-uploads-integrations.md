# 15 — File Uploads & External Integrations

[← Back to index](README.md)

---

## Part A — File uploads

### 1. What can be uploaded

Exactly one thing: **documents**. There is no avatar upload (the `User.avatar`
field is a URL and its model comment says "file uploads arrive in a later
phase"), no attachment on comments, and no import/export of spreadsheets.

### 2. The upload path

```
components/shared/file-upload.tsx        drag-and-drop or click → File object
        ↓ (controlled component; onChange gives the parent a File)
components/documents/document-upload-form.tsx    react-hook-form + zod
        ↓
app/(app)/documents/new/page.tsx  handleSubmit()
        form = new FormData()
        form.append("workspace", activeWorkspaceId)
        form.append("file", values.file)
        form.append("project", ...)  optional
        form.append("title", ...)    optional
        form.append("description", ...) optional
        ↓
hooks/use-documents.ts  useUploadDocument()
        ↓
lib/api/documents.ts    documentsApi.upload(form)
        ↓
lib/api/client.ts       apiClient.post("/documents/", form)
        detects FormData → omits Content-Type → browser sets multipart boundary
        ↓ HTTP POST multipart/form-data
backend/apps/documents/views.py  DocumentViewSet
        parser_classes = (MultiPartParser, FormParser, JSONParser)
        ↓
DocumentSerializer.create()
        file_size    = upload.size
        file_type    = upload.content_type or the extension
        uploaded_by  = request.user
        title        = title or basename(upload.name)
        ↓
Django FileField → STORAGES["default"] (FileSystemStorage)
        path: MEDIA_ROOT/documents/<workspace_id>/<filename>
        ↓
INSERT documents_document
        ↓
post_save → knowledge/handlers.py → embedding pipeline (see Flow 4)
        ↓
201 Created  ← returned immediately; embedding continues in the background
```

### 3. Where files actually live

```python
MEDIA_URL  = "media/"
MEDIA_ROOT = BASE_DIR / "media"      # backend/media/
```
`backend/config/settings/base.py:176-177`

```python
def document_upload_path(instance, filename):
    return f"documents/{instance.workspace_id}/{filename}"
```
`backend/apps/documents/models.py:15-17`

So a file ends up at `backend/media/documents/<workspace-uuid>/<filename>`.
Partitioning by workspace is deliberate — the model comment says it keeps buckets
tidy and migrations storage-agnostic.

In Docker, `media` is a **named volume** mounted at `/app/media` into **both**
`web` and `worker` (`docker-compose.yml:85-88, 111-113`). The worker must see the
same files the web process wrote, or embedding would fail.

### 4. Serving files back

```python
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```
`backend/config/urls.py:54-55` — with the comment *"In production a real object
store (S3/Cloudinary) or the web server handles this."*

`DocumentSerializer.get_file_url` builds an absolute URL via
`request.build_absolute_uri(obj.file.url)`.

> **Production gap.** `DEBUG=False` means Django serves nothing at `/media/`, and
> there is no Nginx config, no `django-storages`, and no S3 configuration in the
> repository. **Uploaded files are not downloadable in a production deployment as
> currently configured.** Recorded in
> [25-known-limitations.md](25-known-limitations.md) as High severity.

### 5. Text extraction

`backend/apps/knowledge/services/extractor.py`

| Extension | Library | Notes |
|---|---|---|
| `.pdf` | `pypdf` | Page by page; empty pages skipped. **No OCR** — a scanned PDF yields no text |
| `.docx` | `python-docx` | Paragraphs **plus table cells**, joined with ` \| ` — "meeting notes often live in tables" |
| `.txt` `.md` `.markdown` | plain read | `decode("utf-8", errors="replace")` — forgiving rather than failing the job |
| anything else | — | `UnsupportedDocumentError`, or skipped silently at the signal |

Both heavy parsers are imported **lazily inside their functions**, so they are
only required when a matching file is actually processed.

`is_supported()` checks **the file extension only** — it ignores the passed
`content_type` entirely (`extractor.py:20-21`).

### 6. Upload security — the honest assessment

| Control | Present? | Evidence |
|---|---|---|
| Authentication | ✅ | `IsAuthenticated` + `IsWorkspaceMember` |
| Workspace scoping of the stored path | ✅ | `document_upload_path` |
| File size limit | ❌ | No `DATA_UPLOAD_MAX_MEMORY_SIZE` or `FILE_UPLOAD_MAX_MEMORY_SIZE` override; no serializer check |
| MIME type whitelist on **upload** | ❌ | Any file type is accepted and stored; only *extraction* is restricted |
| Filename sanitisation | ⚠️ Django's default | `FileSystemStorage.get_valid_name` strips path separators; no custom hardening |
| Filename collision handling | ⚠️ Django's default | Appends a random suffix rather than overwriting |
| Virus scanning | ❌ | None |
| Content-Disposition on serve | ❌ | Files are served by `static()` in dev with no forced download |

**The practical risk:** an authenticated workspace member can upload an arbitrary
file (including HTML or SVG) and, in `DEBUG` mode, get a URL that serves it from
the API origin. Full analysis in [18-security.md](18-security.md).

### 7. Downloads (the other direction)

Two endpoints return files rather than JSON — a handover PDF and the audit-log
CSV. Both go through `frontend/src/lib/api/download.ts`, which cannot use
`apiClient` because that parses JSON. See
[07-api-architecture.md](07-api-architecture.md#7-binary-responses).

---

## Part B — External integrations

Four external systems. Nothing else — no payments, no analytics SDK, no cloud
storage, no ERP.

---

### 1. SMTP (outgoing email)

```
Trigger (invitation created / resent, password reset requested, password changed)
        ↓
apps/common/email.py  queue_templated_email()
        ↓ transaction.on_commit
apps/common/tasks.py  send_email_task.delay()      ← Celery
        ↓  (or inline if the broker is unreachable)
apps/common/email.py  send_templated_email()
        render templates/email/<name>.txt  via the "text" engine (autoescape OFF)
        render templates/email/<name>.html if it exists → attach_alternative
        ↓
EmailMultiAlternatives.send()
        ↓
SMTP server (EMAIL_HOST:EMAIL_PORT, TLS)
```

**Three emails exist:** `invitation`, `password_reset`, `password_changed` —
`backend/templates/email/`.

**Configuration** (`base.py:241-254`): `EMAIL_BACKEND`, `EMAIL_HOST`,
`EMAIL_PORT` (587), `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` `<hidden>`,
`EMAIL_USE_TLS` (True), `EMAIL_TIMEOUT` (10s), `DEFAULT_FROM_EMAIL`,
`FRONTEND_URL`.

**Failure handling, three layers deep:**

| Layer | Behaviour |
|---|---|
| `send_templated_email` | `fail_silently=True` by default — logs and returns 0. "An SMTP outage must not turn an invitation or a password-reset request into a 500." |
| `send_email_task` | Calls it with `fail_silently=False` so Celery *sees* the failure, then `self.retry()` — 3 attempts, 30s/60s/120s backoff |
| `queue_templated_email` | If `.delay()` itself throws (broker down), falls back to sending inline |

**Two subtle correctness details:**

1. **`transaction.on_commit`** — the docstring explains: queuing before the commit
   races the worker, which can mail a link to a row that is not visible yet, or to
   one that never lands because the transaction rolled back.
2. **The `"text"` template engine** — a second `DjangoTemplates` engine with
   `autoescape: False` (`base.py:128-134`). With autoescaping on, an `&` in a
   reset URL renders as `&amp;`, so the link arrives carrying a parameter
   literally named `amp;token` and the reset silently fails. The engine must come
   *after* the default one, because `django.contrib.admin`'s system checks inspect
   the first `DjangoTemplates` engine for the auth and messages context
   processors.

`frontend_url(path)` builds every outgoing link from `settings.FRONTEND_URL`, so
links point at the Next.js app, not the API.

In development the console backend prints emails to the terminal — no SMTP
needed. In Docker the default is also the console backend unless `EMAIL_HOST` is
set.

---

### 2. LLM providers

Three implementations behind one abstract interface.

```python
class BaseLLMProvider(abc.ABC):
    def __init__(self, *, model: str, api_key: str = "", **kwargs)
    @abc.abstractmethod
    def generate(self, messages, *, temperature=0.2, max_tokens=1024) -> LLMResponse
    def stream(self, messages, ...) -> Iterator[str]     # default: one chunk
    @staticmethod
    def _split_system(messages) -> tuple[str, list[dict]]
```
`backend/apps/ai/providers/base.py`

| Provider | SDK | Key | Notes |
|---|---|---|---|
| **Gemini** (default) | `google-generativeai` | `GEMINI_API_KEY` or per-workspace | Translates roles: `assistant` → `model`, content → `parts`. System prompt passed out-of-band as `system_instruction`. True streaming implemented. |
| **OpenAI** | `openai` | `OPENAI_API_KEY` or per-workspace | Standard chat completions |
| **Ollama** | `requests` | none | POSTs to `{OLLAMA_BASE_URL}/api/chat`, 120s timeout. True streaming via `iter_lines()` + per-line JSON |

**Resolution order** (`providers/factory.py:33-62`):

```
settings.AI defaults
   ← overridden by workspace.ai_settings (provider, model, temperature,
     max_tokens, is_enabled, decrypted api_key)
   ← if still no api_key, fall back to the env-level key for that provider
```

Then `get_llm_provider()` raises `ProviderError` if AI is disabled for the
workspace, or if the provider name is unknown.

**Why `_split_system` exists:** some SDKs take the system prompt out-of-band
(Gemini's `system_instruction`) rather than as a message. The base class provides
the split so each provider does not reimplement it.

**Every provider imports its SDK lazily**, inside the method. A missing package
becomes a clean `ProviderError` ("google-generativeai is not installed") instead
of an import-time crash for everyone.

**Every provider wraps failures in `ProviderError`**, which `ai/views.py` turns
into a **502 Bad Gateway** with the message — semantically correct, since the
upstream dependency failed, not this API.

**`stream()` is implemented but unused.** No view calls it; there is no SSE
endpoint. The base class's docstring calls it "the SSE upgrade path". Partially
implemented, by design.

---

### 3. Hugging Face / sentence-transformers (embeddings)

Not an API integration — a **model download plus local inference**.

```python
_MODELS: dict = {}

def _load_model(model_name):
    model = _MODELS.get(model_name)
    if model is None:
        from sentence_transformers import SentenceTransformer   # lazy: pulls torch
        model = SentenceTransformer(model_name)
        _MODELS[model_name] = model
    return model
```
`backend/apps/knowledge/embeddings/sentence_transformer.py:19-27`

| | |
|---|---|
| Model | `all-MiniLM-L6-v2`, 384 dimensions |
| Key required | **None** |
| First call | Downloads ~90 MB from Hugging Face, then caches on disk |
| Subsequent calls | Reuse the in-memory module-level singleton |
| Normalisation | `normalize_embeddings=True` → unit vectors → stable cosine distance |
| Batch size | `EMBED_BATCH_SIZE` = 32 |

Docker caches the download in a named volume mounted at
`/home/nexora/.cache/huggingface` on both `web` and `worker`
(`docker-compose.yml:87-88`) *"so a restart doesn't re-download ~90MB."*

The backend `Dockerfile` installs the **CPU-only torch wheel first**
(`--index-url https://download.pytorch.org/whl/cpu`, line 31) so that the
requirements install does not pull PyPI's default wheel with the entire CUDA
runtime — gigabytes of GPU libraries a CPU embedding worker never loads.

**Provider swapping is stubbed, not implemented.** `embeddings/factory.py:24-29`
recognises `gemini` (768-dim) and `openai` (1536-dim) and raises
`NotImplementedError` with a message that names the required dimension *and*
reminds you a migration altering `DocumentChunk.embedding` is needed first.

---

### 4. Redis

Three unrelated jobs, one server:

| Use | Setting | Fallback when absent |
|---|---|---|
| Celery broker + result backend | `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | `CELERY_TASK_ALWAYS_EAGER=True` → tasks run inline |
| Channels layer | `CHANNEL_LAYER_URL` | `InMemoryChannelLayer` — per-process, single-worker only |
| Throttle counter cache | `CACHE_URL` | `LocMemCache` — per-process counters |

All three default to `REDIS_URL` (`base.py:226`). The development settings switch
each to its in-process equivalent when the corresponding variable is unset, which
is what makes "Postgres only" local development work.

`base.py:222-226` explains why the cache one matters in production: with a
per-process `LocMemCache`, each worker keeps a private throttle counter, so the
effective limit becomes `rate × worker_count`.

---

## Integration failure matrix

| Integration down | Effect | Degrades gracefully? |
|---|---|---|
| SMTP | Invitations and reset links are not delivered. API still returns success. | ✅ (logged, retried 3× by Celery) |
| Celery broker | Tasks run inline in the web process — slower uploads and emails | ✅ |
| Redis (channels) | No websocket push; the client polls every 30s | ✅ |
| Redis (cache) | Throttle counters become per-process | ⚠️ silently weaker limits |
| LLM provider | 502 with the provider's message | ✅ |
| Missing LLM API key | 502 "Gemini API key is not configured for this workspace." | ✅ |
| Hugging Face unreachable on first embed | Job marked `failed` with the error; upload still succeeded | ✅ |
| pgvector extension missing | 503 with a clear admin-facing message | ✅ |
| **PostgreSQL** | `/health/` returns 503; everything else 500s | ❌ hard dependency |

PostgreSQL is the only hard dependency. Every other integration has a documented
fallback — which is the strongest operational property of this codebase.

---

**Next:** [16 — State Management](16-state-management.md)
