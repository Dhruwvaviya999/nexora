"""
Background tasks for the ingestion half of the RAG pipeline.

Embedding a document means loading a transformer model (~90MB) and running it
over every chunk. That is far too slow to hold an upload request open, so the
upload only records an EmbeddingJob and the real work happens here.
"""

from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    ignore_result=True,
)
def process_document_task(self, document_id: str, job_id: str | None = None):
    """Extract, chunk, embed and store one document.

    ``process_document`` already records failures on the job row and does not
    raise, so a retry here is only for the case where the task could not get
    far enough to do that -- a document deleted mid-flight, say.
    """
    from apps.documents.models import Document
    from apps.knowledge.models import EmbeddingJob
    from apps.knowledge.services.processor import process_document

    try:
        document = Document.objects.select_related("workspace").get(pk=document_id)
    except Document.DoesNotExist:
        # Uploaded and deleted again before the worker got to it. Nothing to do.
        logger.info("Document %s no longer exists; skipping embedding", document_id)
        return None

    job = None
    if job_id:
        job = EmbeddingJob.objects.filter(pk=job_id).first()

    result = process_document(document, job=job)
    return str(result.pk)
