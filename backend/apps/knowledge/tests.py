"""
Ingestion pipeline tests.

The point of moving embedding onto a worker is that an upload returns without
waiting for it, so these tests assert the *scheduling* contract -- a job row
exists immediately, the task is dispatched only after the transaction commits,
and a broker outage degrades to inline work rather than losing the document.

The embedding model itself is stubbed: loading it takes tens of seconds and is
not what is under test here.
"""

from __future__ import annotations

from unittest import mock

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from apps.documents.models import Document
from apps.knowledge.models import DocumentChunk, EmbeddingJob, EmbeddingStatus
from apps.knowledge.services.processor import enqueue_document, process_document
from apps.workspaces.models import Workspace

User = get_user_model()

PWD = "Str0ng!Passw0rd"


class StubEmbeddingProvider:
    """Returns a fixed vector per chunk, instantly."""

    name = "stub"
    model_name = "stub-model"

    def embed_texts(self, texts):
        return [[0.1] * 384 for _ in texts]


class ExplodingEmbeddingProvider:
    """Fails the way a provider outage would, after the job row is claimed."""

    name = "exploding"
    model_name = "exploding-model"

    def embed_texts(self, texts):
        raise RuntimeError("model exploded")


class DocumentIngestionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="uploader@example.com", password=PWD, name="Uploader"
        )
        self.workspace = Workspace.objects.create(name="Knowledge", owner=self.user)

    def make_document(self, body=b"Nexora keeps workspace knowledge searchable."):
        return Document.objects.create(
            workspace=self.workspace,
            title="Notes",
            file=SimpleUploadedFile("notes.txt", body, content_type="text/plain"),
            file_type="text/plain",
            uploaded_by=self.user,
        )

    # -- scheduling ------------------------------------------------------
    def test_enqueue_returns_a_pending_job_without_doing_the_work(self):
        document = self.make_document()

        with self.captureOnCommitCallbacks():  # do not run the callback
            job = enqueue_document(document)

        self.assertEqual(job.status, EmbeddingStatus.PENDING)
        self.assertEqual(
            DocumentChunk.objects.filter(document=document).count(),
            0,
            "embedding ran inside the request instead of being deferred",
        )

    def test_the_task_is_dispatched_only_after_commit(self):
        document = self.make_document()

        with mock.patch(
            "apps.knowledge.tasks.process_document_task.delay"
        ) as delay:
            with self.captureOnCommitCallbacks(execute=False):
                enqueue_document(document)
            self.assertEqual(
                delay.call_count, 0, "the task was queued before the commit"
            )

        with mock.patch("apps.knowledge.tasks.process_document_task.delay") as delay:
            with self.captureOnCommitCallbacks(execute=True):
                job = enqueue_document(document)
            delay.assert_called_once_with(str(document.pk), str(job.pk))

    def test_a_broker_outage_falls_back_to_processing_inline(self):
        """Better a slow upload than a document that is never indexed."""
        document = self.make_document()

        with mock.patch(
            "apps.knowledge.tasks.process_document_task.delay",
            side_effect=OSError("broker unreachable"),
        ), mock.patch(
            "apps.knowledge.services.processor.get_embedding_provider",
            return_value=StubEmbeddingProvider(),
        ), self.assertLogs("apps.knowledge.services.processor", level="ERROR"):
            with self.captureOnCommitCallbacks(execute=True):
                job = enqueue_document(document)

        job.refresh_from_db()
        self.assertEqual(job.status, EmbeddingStatus.COMPLETED)
        self.assertGreater(DocumentChunk.objects.filter(document=document).count(), 0)

    # -- processing ------------------------------------------------------
    def test_processing_stores_chunks_and_completes_the_job(self):
        document = self.make_document()

        with mock.patch(
            "apps.knowledge.services.processor.get_embedding_provider",
            return_value=StubEmbeddingProvider(),
        ):
            job = process_document(document)

        self.assertEqual(job.status, EmbeddingStatus.COMPLETED)
        self.assertEqual(job.provider, "stub")
        chunks = DocumentChunk.objects.filter(document=document)
        self.assertGreater(chunks.count(), 0)
        self.assertEqual(job.chunk_count, chunks.count())

    def test_reprocessing_replaces_chunks_rather_than_duplicating_them(self):
        document = self.make_document()

        with mock.patch(
            "apps.knowledge.services.processor.get_embedding_provider",
            return_value=StubEmbeddingProvider(),
        ):
            process_document(document)
            first = DocumentChunk.objects.filter(document=document).count()
            process_document(document)
            second = DocumentChunk.objects.filter(document=document).count()

        self.assertEqual(first, second, "re-indexing duplicated the chunks")

    def test_a_failure_is_recorded_on_the_job_not_raised(self):
        document = self.make_document()

        with mock.patch(
            "apps.knowledge.services.processor.get_embedding_provider",
            return_value=ExplodingEmbeddingProvider(),
        ), self.assertLogs("apps.knowledge.services.processor", level="ERROR"):
            job = process_document(document)

        self.assertEqual(job.status, EmbeddingStatus.FAILED)
        self.assertIn("model exploded", job.error)

    def test_the_task_tolerates_a_document_deleted_before_it_ran(self):
        from apps.knowledge.tasks import process_document_task

        document = self.make_document()
        document_id = str(document.pk)
        document.delete()

        # Must not raise -- the worker would otherwise retry forever.
        self.assertIsNone(process_document_task(document_id))

    def test_uploading_a_document_creates_a_job(self):
        """The upload signal still schedules ingestion."""
        with self.captureOnCommitCallbacks():
            document = self.make_document()

        self.assertTrue(
            EmbeddingJob.objects.filter(document=document).exists(),
            "uploading a document did not schedule embedding",
        )
