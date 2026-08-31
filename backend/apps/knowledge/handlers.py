"""
Signal wiring that drives the embedding pipeline.

When a Document is first created with a supported, extractable file, kick off
processing. File *replacements* and manual re-runs go through the documents
``reindex`` action instead, so metadata-only edits (title/description) never
trigger expensive re-embedding.

Processing runs inline today (no Celery yet) and is wrapped in a broad guard:
a failed embedding must never break the upload response.
"""

import contextlib
import logging

from django.db.models.signals import post_save

from apps.documents.models import Document
from apps.knowledge.services import extractor
from apps.knowledge.services.processor import enqueue_document

logger = logging.getLogger(__name__)


def _on_document_created(sender, instance, created, **kwargs):
    if not created or not instance.file:
        return
    if not extractor.is_supported(instance.file.name, instance.file_type):
        # Nothing to embed (e.g. an image or archive) — skip silently.
        return
    try:
        enqueue_document(instance)
    except Exception:  # noqa: BLE001 — never let ingestion break the upload
        logger.exception("Failed to enqueue embedding for document %s", instance.pk)


post_save.connect(
    _on_document_created,
    sender=Document,
    weak=False,
    dispatch_uid="knowledge_document_created",
)


@contextlib.contextmanager
def ingestion_disabled():
    """Stop new documents scheduling embedding, for this block only.

    Bulk loaders (the demo seeder) use this to avoid embedding hundreds of
    documents. It restores the signal on the way out: disconnecting without
    reconnecting leaves the process silently unable to index anything for as
    long as it lives.
    """
    post_save.disconnect(sender=Document, dispatch_uid="knowledge_document_created")
    try:
        yield
    finally:
        post_save.connect(
            _on_document_created,
            sender=Document,
            weak=False,
            dispatch_uid="knowledge_document_created",
        )
