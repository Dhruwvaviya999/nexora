import os

from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from apps.documents.models import Document


class DocumentSerializer(serializers.ModelSerializer):
    uploaded_by = UserSerializer(read_only=True)
    created_by = UserSerializer(read_only=True)
    updated_by = UserSerializer(read_only=True)
    file_url = serializers.SerializerMethodField()

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
            "uploaded_by",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        )
        extra_kwargs = {"file": {"write_only": True, "required": False}}

    def get_file_url(self, obj) -> str | None:
        if not obj.file:
            return None
        request = self.context.get("request")
        url = obj.file.url
        return request.build_absolute_uri(url) if request else url

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
