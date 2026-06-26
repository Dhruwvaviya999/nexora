from drf_spectacular.utils import extend_schema
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser

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
