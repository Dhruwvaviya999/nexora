import os

from django.conf import settings
from django.urls import reverse
from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from apps.documents.models import Document

# Uploads are accepted only for types the product can actually do something
# with: extract text from, or display. Anything else is rejected at the door
# rather than stored and served back later.
ALLOWED_UPLOAD_EXTENSIONS = {
    # Text-extractable — these feed the RAG pipeline.
    ".pdf", ".docx", ".txt", ".md", ".markdown",
    # Common attachments, stored but not embedded.
    ".csv", ".xlsx", ".pptx", ".png", ".jpg", ".jpeg", ".gif", ".webp",
}


class DocumentSerializer(serializers.ModelSerializer):
    uploaded_by = UserSerializer(read_only=True)
    created_by = UserSerializer(read_only=True)
    updated_by = UserSerializer(read_only=True)
    file_url = serializers.SerializerMethodField()
    # Phase 5 — RAG ingestion status, surfaced so the UI can show progress.
    embedding_status = serializers.SerializerMethodField()
    chunk_count = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = (
            "id",
            "workspace",
            "project",
            "title",
            "description",
            "file",
            "file_url",
            "file_type",
            "file_size",
            "embedding_status",
            "chunk_count",
            "uploaded_by",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "file_url",
            "file_type",
            "file_size",
            "embedding_status",
            "chunk_count",
            "uploaded_by",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        )
        extra_kwargs = {
            "file": {"write_only": True, "required": False},
            # `Document.title` is a non-blank CharField, so DRF would infer
            # required=True -- which made the filename fallback in create()
            # unreachable and rejected any upload that omitted a title (the
            # frontend sends it only when the user typed one).
            "title": {"required": False, "allow_blank": True},
        }

    def get_file_url(self, obj) -> str | None:
        """Absolute URL of the authenticated download endpoint.

        Deliberately *not* ``obj.file.url``: that is a public media path, which
        would be an unauthenticated cross-tenant read, and it 404s in
        production because Django only serves /media/ while DEBUG is on.
        """
        if not obj.file:
            return None
        request = self.context.get("request")
        path = reverse("v1:documents:document-download", kwargs={"pk": obj.pk})
        return request.build_absolute_uri(path) if request else path

    def get_embedding_status(self, obj) -> str | None:
        # Latest embedding job's status, or None if the doc was never processed.
        job = obj.embedding_jobs.order_by("-created_at").first()
        return job.status if job else None

    def get_chunk_count(self, obj) -> int:
        return obj.chunks.count()

    def validate_file(self, value):
        """Bound the size and the type of anything we agree to store.

        Without this, any member could fill the disk, or upload an .html/.svg
        that would execute on the API's origin if it were ever served inline.
        (The download view forces ``Content-Disposition: attachment`` as a
        second line of defence.)
        """
        if value is None:
            return value

        max_bytes = settings.MAX_UPLOAD_SIZE
        if value.size > max_bytes:
            raise serializers.ValidationError(
                f"File is too large ({value.size / 1024 / 1024:.1f} MB). "
                f"The limit is {max_bytes // (1024 * 1024)} MB."
            )

        extension = os.path.splitext(value.name)[1].lower()
        if extension not in ALLOWED_UPLOAD_EXTENSIONS:
            allowed = ", ".join(sorted(ALLOWED_UPLOAD_EXTENSIONS))
            raise serializers.ValidationError(
                f"Unsupported file type '{extension or 'unknown'}'. Allowed: {allowed}."
            )
        return value

    def validate(self, attrs):
        # File is required on create, optional on update (metadata-only edits).
        if self.instance is None and not attrs.get("file"):
            raise serializers.ValidationError({"file": "A file is required."})
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        upload = validated_data.get("file")
        if upload is not None:
            validated_data["file_size"] = upload.size
            validated_data["file_type"] = (
                getattr(upload, "content_type", "")
                or os.path.splitext(upload.name)[1].lstrip(".")
            )
        if request and request.user.is_authenticated:
            validated_data["uploaded_by"] = request.user
        # Default the title to the filename when omitted.
        if not validated_data.get("title") and upload is not None:
            validated_data["title"] = os.path.basename(upload.name)
        return super().create(validated_data)
