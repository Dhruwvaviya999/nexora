"""Comment API."""

from django.contrib.contenttypes.models import ContentType
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.comments.models import Comment
from apps.comments.permissions import IsAuthorOrWorkspaceAdmin
from apps.comments.serializers import ALLOWED_TARGETS, CommentSerializer


@extend_schema(tags=["comments"])
class CommentViewSet(viewsets.ModelViewSet):
    """Comments on projects, tasks and documents.

    List is filtered by ``?target_type=&target_id=`` and always scoped to
    workspaces the user belongs to. Create derives the workspace/target from
    either the explicit target or the parent comment being replied to.
    """

    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated, IsAuthorOrWorkspaceAdmin]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Comment.objects.none()

        qs = (
            Comment.objects.filter(workspace__members__user=self.request.user)
            .select_related("author", "content_type")
            .distinct()
        )

        params = self.request.query_params
        target_type = params.get("target_type")
        target_id = params.get("target_id")

        if target_type in ALLOWED_TARGETS:
            qs = qs.filter(content_type=self._content_type(target_type))
        if target_id:
            qs = qs.filter(object_id=target_id)

        return qs

    @staticmethod
    def _content_type(target_type: str) -> ContentType:
        app_label, model = ALLOWED_TARGETS[target_type]
        return ContentType.objects.get_by_natural_key(app_label, model)

    def _resolve_target(self, serializer):
        """Work out (workspace, content_type, object_id) for a new comment and
        confirm the user is a member of the relevant workspace."""
        parent = serializer.validated_data.get("parent")

        if parent is not None:
            if parent.is_deleted:
                raise ValidationError({"parent": "Cannot reply to a deleted comment."})
            workspace = parent.workspace
            content_type = parent.content_type
            object_id = parent.object_id
        else:
            target_type = serializer.validated_data.pop("target_type", None)
            object_id = serializer.validated_data.pop("target_id", None)
            if not target_type or not object_id:
                raise ValidationError(
                    {"target_type": "target_type and target_id are required."}
                )
            content_type = self._content_type(target_type)
            target = content_type.get_object_for_this_type(pk=object_id)
            workspace = target.workspace

        if not workspace.members.filter(user=self.request.user).exists():
            raise PermissionDenied("You are not a member of this workspace.")

        # Drop write-only keys so they don't reach the model on save.
        serializer.validated_data.pop("target_type", None)
        serializer.validated_data.pop("target_id", None)
        return workspace, content_type, object_id

    def perform_create(self, serializer):
        workspace, content_type, object_id = self._resolve_target(serializer)
        serializer.save(
            author=self.request.user,
            workspace=workspace,
            content_type=content_type,
            object_id=object_id,
        )

    def perform_update(self, serializer):
        serializer.save(is_edited=True)

    def destroy(self, request, *args, **kwargs):
        comment = self.get_object()
        comment.is_deleted = True
        comment.content = ""
        comment.save(update_fields=["is_deleted", "content", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(request=CommentSerializer, responses={201: CommentSerializer})
    @action(detail=True, methods=["post"])
    def reply(self, request, pk=None):
        """POST /comments/{id}/reply/ — convenience endpoint for threaded replies."""
        parent = self.get_object()
        serializer = self.get_serializer(
            data={"content": request.data.get("content", ""), "parent": str(parent.pk)}
        )
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
