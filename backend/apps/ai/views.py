"""
AI app API.

* ViewSets (conversations, search history, prompt templates) reuse the project's
  workspace-scoping conventions.
* The action endpoints (chat/search/summarize/generate-tasks/settings) are
  APIViews because the workspace arrives in the body; each verifies membership
  via ``resolve_workspace`` before doing any retrieval — the isolation gate.
"""

from __future__ import annotations

from django.db import DatabaseError
from django.db.models import Q
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai.models import (
    AIConversation,
    AIMessage,
    AISettings,
    MessageRole,
    PromptTemplate,
    SearchHistory,
)
from apps.ai.permissions import resolve_workspace
from apps.ai.providers.base import ProviderError
from apps.ai.serializers import (
    AIConversationDetailSerializer,
    AIConversationSerializer,
    AISettingsSerializer,
    ChatRequestSerializer,
    GenerateTasksRequestSerializer,
    PromptTemplateSerializer,
    SearchHistorySerializer,
    SearchRequestSerializer,
    SummarizeRequestSerializer,
)
from apps.ai.services import rag
from apps.ai.services.action_items import ActionItemError, generate_tasks
from apps.ai.services.summarizer import SummaryError, summarize
from apps.common.viewsets import WorkspaceScopedViewSet
from apps.knowledge.services.search import semantic_search

# How many prior turns to feed back into a chat request as context.
_HISTORY_TURNS = 10


def _provider_error_response(exc: Exception) -> Response:
    return Response(
        {"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY
    )


def _retrieval_unavailable_response() -> Response:
    """Clean error when the vector store isn't ready (e.g. pgvector/migration
    not yet installed) instead of leaking a 500 to the client."""
    return Response(
        {
            "detail": (
                "Semantic search isn't available yet. The vector index has not "
                "been set up for this deployment — ask an admin to finish AI "
                "setup (install pgvector and run migrations)."
            )
        },
        status=status.HTTP_503_SERVICE_UNAVAILABLE,
    )


@extend_schema(tags=["ai"])
class AIConversationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Read/delete chat threads. Creation happens through the chat endpoint."""

    permission_classes = [IsAuthenticated]
    serializer_class = AIConversationSerializer
    filterset_fields = ("workspace",)
    ordering = ("-updated_at",)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return AIConversation.objects.none()
        # Conversations are private to their owner within the workspace.
        return (
            AIConversation.objects.filter(
                user=self.request.user,
                workspace__members__user=self.request.user,
            )
            .select_related("user", "workspace")
            .distinct()
        )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return AIConversationDetailSerializer
        return AIConversationSerializer


@extend_schema(tags=["ai"])
class SearchHistoryViewSet(
    mixins.ListModelMixin, viewsets.GenericViewSet
):
    permission_classes = [IsAuthenticated]
    serializer_class = SearchHistorySerializer
    filterset_fields = ("workspace",)
    ordering = ("-created_at",)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return SearchHistory.objects.none()
        return SearchHistory.objects.filter(
            user=self.request.user,
            workspace__members__user=self.request.user,
        ).distinct()


@extend_schema(tags=["ai"])
class PromptTemplateViewSet(WorkspaceScopedViewSet):
    queryset = PromptTemplate.objects.select_related("workspace", "created_by")
    serializer_class = PromptTemplateSerializer
    filterset_fields = ("workspace", "category")
    search_fields = ("name", "description")
    ordering_fields = ("name", "created_at")
    ordering = ("name",)

    def get_queryset(self):
        qs = super().get_queryset()
        # Show shared templates plus the user's own private ones.
        return qs.filter(Q(is_shared=True) | Q(created_by=self.request.user))


@extend_schema(tags=["ai"])
class ChatView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=ChatRequestSerializer,
        responses={200: OpenApiResponse(description="Assistant reply + sources")},
    )
    def post(self, request):
        payload = ChatRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        workspace = resolve_workspace(request.user, data["workspace"])

        conversation = self._get_or_create_conversation(
            request.user, workspace, data.get("conversation"), data["message"]
        )

        # Persist the user's message first so history is consistent on failure.
        AIMessage.objects.create(
            conversation=conversation,
            role=MessageRole.USER,
            content=data["message"],
        )

        history = self._recent_history(conversation)
        try:
            result = rag.answer_question(
                workspace=workspace,
                query=data["message"],
                history=history,
            )
        except DatabaseError:
            return _retrieval_unavailable_response()
        except ProviderError as exc:
            return _provider_error_response(exc)

        assistant = AIMessage.objects.create(
            conversation=conversation,
            role=MessageRole.ASSISTANT,
            content=result["answer"],
            sources=result["sources"],
            metadata={
                "confidence": result["confidence"],
                "top_score": result["top_score"],
                "model": result["model"],
            },
        )
        # Touch the conversation so it sorts to the top of the list.
        conversation.save(update_fields=["updated_at"])

        return Response(
            {
                "conversation": str(conversation.id),
                "message": {
                    "id": str(assistant.id),
                    "role": assistant.role,
                    "content": assistant.content,
                    "sources": assistant.sources,
                    "created_at": assistant.created_at,
                },
                "confidence": result["confidence"],
            },
            status=status.HTTP_200_OK,
        )

    def _get_or_create_conversation(self, user, workspace, conversation_id, first_msg):
        if conversation_id:
            conversation = AIConversation.objects.filter(
                pk=conversation_id, workspace=workspace, user=user
            ).first()
            if conversation is None:
                from rest_framework.exceptions import NotFound

                raise NotFound("Conversation not found.")
            return conversation
        return AIConversation.objects.create(
            workspace=workspace,
            user=user,
            title=first_msg[:80],
            created_by=user,
            updated_by=user,
        )

    @staticmethod
    def _recent_history(conversation) -> list[dict]:
        msgs = conversation.messages.order_by("-created_at")[:_HISTORY_TURNS]
        return [
            {"role": m.role, "content": m.content}
            for m in reversed(list(msgs))
        ]


@extend_schema(tags=["ai"])
class SearchView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=SearchRequestSerializer)
    def post(self, request):
        payload = SearchRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        workspace = resolve_workspace(request.user, data["workspace"])

        try:
            results = semantic_search(
                workspace=workspace, query=data["query"], limit=data.get("limit")
            )
        except DatabaseError:
            return _retrieval_unavailable_response()
        sources = [
            {
                "chunk_id": str(r.chunk.id),
                "document_id": str(r.chunk.document_id),
                "title": r.chunk.metadata.get("title")
                or getattr(r.chunk.document, "title", "Untitled"),
                "content": r.chunk.content,
                "chunk_index": r.chunk.chunk_index,
                "score": r.score,
            }
            for r in results
        ]
        top_score = sources[0]["score"] if sources else 0.0

        SearchHistory.objects.create(
            workspace=workspace,
            user=request.user,
            query=data["query"][:1000],
            results_count=len(sources),
            top_score=top_score,
        )

        return Response(
            {
                "query": data["query"],
                "results": sources,
                "count": len(sources),
                "top_score": top_score,
            }
        )


@extend_schema(tags=["ai"])
class SummarizeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=SummarizeRequestSerializer)
    def post(self, request):
        payload = SummarizeRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        workspace = resolve_workspace(request.user, data["workspace"])
        try:
            result = summarize(
                workspace=workspace,
                target_type=data["target_type"],
                target_id=data.get("target_id"),
                period=data.get("period", "week"),
            )
        except SummaryError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except ProviderError as exc:
            return _provider_error_response(exc)
        return Response(result)


@extend_schema(tags=["ai"])
class GenerateTasksView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=GenerateTasksRequestSerializer)
    def post(self, request):
        payload = GenerateTasksRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        workspace = resolve_workspace(request.user, data["workspace"])
        try:
            result = generate_tasks(
                workspace=workspace,
                document_id=data.get("document"),
                text=data.get("text"),
            )
        except ActionItemError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except ProviderError as exc:
            return _provider_error_response(exc)
        return Response(result)


@extend_schema(tags=["ai"])
class AISettingsView(APIView):
    """GET/PATCH per-workspace AI settings. Editing requires admin."""

    permission_classes = [IsAuthenticated]

    def _get_settings(self, workspace):
        obj, _ = AISettings.objects.get_or_create(workspace=workspace)
        return obj

    def get(self, request):
        workspace_id = request.query_params.get("workspace")
        if not workspace_id:
            return Response(
                {"detail": "workspace query param is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        workspace = resolve_workspace(request.user, workspace_id)
        settings_obj = self._get_settings(workspace)
        return Response(AISettingsSerializer(settings_obj).data)

    def patch(self, request):
        workspace_id = request.data.get("workspace")
        if not workspace_id:
            return Response(
                {"detail": "workspace is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Only owners/admins may change AI settings (keys, provider, etc.).
        workspace = resolve_workspace(request.user, workspace_id, require_admin=True)
        settings_obj = self._get_settings(workspace)
        serializer = AISettingsSerializer(
            settings_obj, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
