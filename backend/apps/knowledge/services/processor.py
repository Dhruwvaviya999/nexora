"""
Document processor — orchestrates the ingestion half of the RAG pipeline:

    extract text -> chunk -> embed -> store DocumentChunk rows

``enqueue_document`` is the single entry point used by the upload signal and the
``reindex`` action. It records the job and hands the work to a Celery worker, so
an upload returns as soon as the file is stored rather than waiting on the
embedding model. With CELERY_TASK_ALWAYS_EAGER (development, tests) the same
call runs inline instead, which keeps local setup down to Postgres alone.
"""

from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone

from apps.knowledge.embeddings import get_embedding_provider
from apps.knowledge.models import DocumentChunk, EmbeddingJob, EmbeddingStatus
from apps.knowledge.services import extractor
from apps.knowledge.services.chunker import chunk_text

logger = logging.getLogger(__name__)


def enqueue_document(document) -> EmbeddingJob:
    """Schedule (re)processing of ``document`` on a worker.

    Returns the pending EmbeddingJob immediately; callers poll its status
    through the document's ``embedding_status`` field.
    """
    job = EmbeddingJob.objects.create(
        workspace=document.workspace,
        document=document,
        status=EmbeddingStatus.PENDING,
    )

    document_id, job_id = str(document.pk), str(job.pk)

    def dispatch():
        # Imported here to avoid a circular import: tasks -> processor -> tasks.
        from apps.knowledge.tasks import process_document_task

        try:
            process_document_task.delay(document_id, job_id)
        except Exception:  # noqa: BLE001 -- broker down: better slow than lost
            logger.exception(
                "Could not queue embedding for document %s; running inline",
                document_id,
            )
            process_document(document, job=job)

    # Queued after commit so the worker cannot read the document row before it
    # exists -- the upload is still inside its transaction at this point.
    transaction.on_commit(dispatch)
    return job


def process_document(document, job: EmbeddingJob | None = None) -> EmbeddingJob:
    """Extract, chunk, embed and store one document. Idempotent (replaces chunks)."""
    if job is None:
        job = EmbeddingJob.objects.create(
            workspace=document.workspace,
            document=document,
            status=EmbeddingStatus.PENDING,
        )

    provider = get_embedding_provider()
    job.status = EmbeddingStatus.PROCESSING
    job.provider = provider.name
    job.model = getattr(provider, "model_name", "")
    job.started_at = timezone.now()
    job.error = ""
    job.save(update_fields=["status", "provider", "model", "started_at", "error"])

    try:
        if not document.file:
            raise extractor.UnsupportedDocumentError("Document has no file.")

        filename = document.file.name
        if not extractor.is_supported(filename, document.file_type):
            raise extractor.UnsupportedDocumentError(
                f"Cannot extract text from {filename!r}."
            )

        with document.file.open("rb") as fh:
            text = extractor.extract_text(fh, filename, document.file_type)

        chunks = chunk_text(text)
        if chunks:
            vectors = provider.embed_texts([c["content"] for c in chunks])
        else:
            vectors = []

        _store_chunks(document, chunks, vectors)

        job.chunk_count = len(chunks)
        job.status = EmbeddingStatus.COMPLETED
        job.finished_at = timezone.now()
        job.save(update_fields=["chunk_count", "status", "finished_at"])
    except Exception as exc:  # noqa: BLE001 — record failure, never crash upload
        logger.exception("Embedding job failed for document %s", document.pk)
        job.status = EmbeddingStatus.FAILED
        job.error = str(exc)[:2000]
        job.finished_at = timezone.now()
        job.save(update_fields=["status", "error", "finished_at"])
    return job


@transaction.atomic
def _store_chunks(document, chunks: list[dict], vectors: list[list[float]]) -> None:
    """Replace this document's chunks atomically (re-index safe)."""
    DocumentChunk.objects.filter(document=document).delete()
    rows = [
        DocumentChunk(
            workspace=document.workspace,
            document=document,
            content=chunk["content"],
            chunk_index=chunk["chunk_index"],
            token_count=chunk["token_count"],
            embedding=vector,
            metadata={"title": document.title},
        )
        for chunk, vector in zip(chunks, vectors)
    ]
    DocumentChunk.objects.bulk_create(rows, batch_size=200)
