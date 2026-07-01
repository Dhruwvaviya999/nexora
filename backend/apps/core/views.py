"""Core API views: service-level endpoints not tied to a domain model."""

from django.db import connection
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.serializers import DashboardSerializer
from apps.documents.models import Document
from apps.documents.serializers import DocumentSerializer
from apps.projects.models import Project, ProjectStatus
from apps.projects.serializers import ProjectSerializer
from apps.tasks.models import Task, TaskStatus
from apps.tasks.serializers import TaskSerializer
from apps.workspaces.models import Workspace


class HealthCheckView(APIView):
    """Liveness/readiness probe.

    Returns ``200`` with ``{"status": "ok"}`` when the service and its database
    connection are healthy, ``503`` otherwise. Public on purpose so uptime
    monitors and orchestrators can reach it without a token.
    """

    permission_classes = [AllowAny]
    authentication_classes: list = []

    @extend_schema(
        summary="Health check",
        description="Reports service and database health.",
        responses={200: None, 503: None},
        tags=["core"],
    )
    def get(self, request: Request) -> Response:
        database_ok = True
        try:
            connection.ensure_connection()
        except Exception:  # pragma: no cover - exercised only when DB is down
            database_ok = False

        payload = {
            "status": "ok" if database_ok else "degraded",
            "service": "ai-knowledge-workflow-assistant",
            "version": "v1",
            "database": "ok" if database_ok else "unavailable",
        }
        http_status = (
            status.HTTP_200_OK if database_ok else status.HTTP_503_SERVICE_UNAVAILABLE
        )
        return Response(payload, status=http_status)


# Task statuses considered "open"/pending work.
OPEN_TASK_STATUSES = (
    TaskStatus.TODO,
    TaskStatus.IN_PROGRESS,
    TaskStatus.REVIEW,
)


@extend_schema(tags=["dashboard"])
class DashboardView(APIView):
    """GET /dashboard/?workspace=<id> — aggregated stats + recent items.

    Scoped to a single workspace the requesting user belongs to.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = DashboardSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="workspace",
                type=str,
                required=True,
                description="Workspace id to report on.",
            )
        ],
        responses=DashboardSerializer,
    )
    def get(self, request: Request) -> Response:
        workspace_id = request.query_params.get("workspace")
        if not workspace_id:
            raise ValidationError({"workspace": "This query parameter is required."})

        # 404 if the workspace doesn't exist OR the user isn't a member of it.
        workspace = get_object_or_404(
            Workspace.objects.filter(members__user=request.user).distinct(),
            pk=workspace_id,
        )

        projects = Project.objects.filter(workspace=workspace)
        tasks = Task.objects.filter(workspace=workspace)
        documents = Document.objects.filter(workspace=workspace)
        today = timezone.now().date()

        stats = {
            "total_projects": projects.count(),
            "active_projects": projects.filter(
                status=ProjectStatus.ACTIVE, archived=False
            ).count(),
            "archived_projects": projects.filter(archived=True).count(),
            "total_tasks": tasks.count(),
            "pending_tasks": tasks.filter(status__in=OPEN_TASK_STATUSES).count(),
            "completed_tasks": tasks.filter(status=TaskStatus.COMPLETED).count(),
            "overdue_tasks": tasks.filter(
                due_date__lt=today, status__in=OPEN_TASK_STATUSES
            ).count(),
            "total_documents": documents.count(),
        }

        ctx = {"request": request}
        payload = {
            "stats": stats,
            "recent_projects": ProjectSerializer(
                projects.select_related("owner", "created_by")[:5],
                many=True,
                context=ctx,
            ).data,
            "recent_tasks": TaskSerializer(
                tasks.select_related("project", "assignee")[:5], many=True, context=ctx
            ).data,
            "recent_documents": DocumentSerializer(
                documents.select_related("uploaded_by")[:5], many=True, context=ctx
            ).data,
        }
        return Response(payload)
