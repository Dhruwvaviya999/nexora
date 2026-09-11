import mimetypes

from django.http import FileResponse, Http404
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.common.viewsets import WorkspaceScopedViewSet
from apps.documents.filters import DocumentFilter
from apps.documents.models import Document
from apps.documents.serializers import DocumentSerializer


@extend_schema(tags=["documents"])
class DocumentViewSet(WorkspaceScopedViewSet):
    queryset = Document.objects.select_related(
        "workspace", "project", "uploaded_by", "created_by", "updated_by"
    )
    serializer_class = DocumentSerializer
    filterset_class = DocumentFilter
    search_fields = ("title", "description")
    ordering_fields = ("created_at", "updated_at", "title", "file_size")
    ordering = ("-created_at",)
    # Accept multipart uploads as well as JSON metadata edits.
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    @extend_schema(
        summary="Download the document's file",
        responses={(200, "application/octet-stream"): bytes},
    )
    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        """GET /documents/{id}/download/ — stream the file to a member.

        Uploads are never exposed at a public ``/media/`` URL. Two reasons:

        1. **Tenancy.** A raw media path is an unauthenticated read. Anyone
           holding (or guessing) the URL could fetch another workspace's file,
           which would bypass every permission check in the project.
        2. **Deployment.** ``django.conf.urls.static`` only serves media while
           ``DEBUG`` is on, so with ``DEBUG=False`` those URLs 404 unless a web
           server is configured to serve the directory. Going through a view
           works identically on local disk and on S3.

        ``get_object()`` applies the usual workspace-membership filter, so a
        non-member gets 404 here exactly as they would on the detail route.
        """
        document = self.get_object()
        if not document.file:
            raise Http404("This document has no file.")

        # Trust the extension over the stored content_type: file_type is
        # populated from the client-supplied MIME type at upload time.
        content_type = (
            mimetypes.guess_type(document.file.name)[0] or "application/octet-stream"
        )

        try:
            handle = document.file.open("rb")
        except FileNotFoundError as exc:  # storage and database disagree
            raise Http404("The stored file is missing.") from exc

        # FileResponse streams in chunks and closes the handle itself, so a
        # large PDF is never buffered into memory.
        response = FileResponse(handle, content_type=content_type)
        # Always an attachment: an uploaded .html or .svg served inline would
        # execute on the API's origin.
        response["Content-Disposition"] = (
            f'attachment; filename="{_safe_filename(document)}"'
        )
        response["Content-Length"] = document.file_size or document.file.size
        response["X-Content-Type-Options"] = "nosniff"
        return response

    @extend_schema(
        request=None,
        responses={202: OpenApiResponse(description="Re-embedding triggered")},
    )
    @action(detail=True, methods=["post"])
    def reindex(self, request, pk=None):
        """Re-run text extraction, chunking and embedding for this document."""
        # Imported here to keep the documents app importable without the AI stack.
        from apps.knowledge.services.processor import enqueue_document

        document = self.get_object()
        job = enqueue_document(document)
        return Response(
            {
                "document": str(document.id),
                "status": job.status,
                "chunk_count": job.chunk_count,
                "error": job.error,
            },
            status=202,
        )


def _safe_filename(document) -> str:
    """A download filename that cannot break out of the header.

    Quotes and newlines would let a crafted title inject extra response header
    directives, so they are stripped rather than escaped.
    """
    import os

    name = os.path.basename(document.file.name) or "document"
    return "".join(c for c in name if c.isprintable() and c not in '"\\\r\n')
