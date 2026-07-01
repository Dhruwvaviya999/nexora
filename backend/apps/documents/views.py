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
