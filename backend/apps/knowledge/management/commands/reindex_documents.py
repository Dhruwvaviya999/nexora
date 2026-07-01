"""
Re-embed documents in bulk.

Useful after enabling Phase 5 on an existing database (documents uploaded before
the pipeline existed) or after changing the chunking/embedding configuration.

    python manage.py reindex_documents
    python manage.py reindex_documents --workspace <workspace_id>
    python manage.py reindex_documents --only-missing
"""

from django.core.management.base import BaseCommand

from apps.documents.models import Document
from apps.knowledge.services import extractor
from apps.knowledge.services.processor import process_document


class Command(BaseCommand):
    help = "Extract, chunk and embed documents into the vector store."

    def add_arguments(self, parser):
        parser.add_argument(
            "--workspace",
            dest="workspace",
            help="Limit to a single workspace id.",
        )
        parser.add_argument(
            "--only-missing",
            action="store_true",
            help="Skip documents that already have chunks.",
        )

    def handle(self, *args, **options):
        qs = Document.objects.all().select_related("workspace")
        if options.get("workspace"):
            qs = qs.filter(workspace_id=options["workspace"])

        processed = skipped = failed = 0
        for document in qs.iterator():
            if not document.file or not extractor.is_supported(
                document.file.name, document.file_type
            ):
                skipped += 1
                continue
            if options.get("only_missing") and document.chunks.exists():
                skipped += 1
                continue

            job = process_document(document)
            if job.status == "completed":
                processed += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ {document.title} ({job.chunk_count} chunks)"
                    )
                )
            else:
                failed += 1
                self.stdout.write(
                    self.style.ERROR(f"✗ {document.title}: {job.error}")
                )

        self.stdout.write(
            self.style.NOTICE(
                f"Done. processed={processed} skipped={skipped} failed={failed}"
            )
        )
