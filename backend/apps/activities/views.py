"""Activity feed API (read-only) — powers workspace/project/task timelines
and the audit-log screen (filters + CSV export)."""

import csv

from django.http import HttpResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from apps.activities.models import Activity
from apps.activities.serializers import ActivitySerializer

# Hard cap on CSV export size to keep the response bounded.
EXPORT_LIMIT = 10_000


@extend_schema(tags=["activities"])
class ActivityViewSet(viewsets.ReadOnlyModelViewSet):
    """Activity scoped to the user's workspaces.

    Filters: ``?workspace=<id>``, ``?action=task.created``, ``?actor=<user id>``,
    ``?date_from=YYYY-MM-DD``, ``?date_to=YYYY-MM-DD``,
    ``?target_type=task`` and ``?target_id=<uuid>`` (for per-object timelines).
    """

    serializer_class = ActivitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Activity.objects.none()

        qs = (
            Activity.objects.filter(workspace__members__user=self.request.user)
            .select_related("actor", "content_type")
            .distinct()
        )

        params = self.request.query_params
        if params.get("workspace"):
            qs = qs.filter(workspace_id=params["workspace"])
        if params.get("action"):
            qs = qs.filter(action=params["action"])
        if params.get("actor"):
            qs = qs.filter(actor_id=params["actor"])
        if params.get("date_from"):
            qs = qs.filter(created_at__date__gte=params["date_from"])
        if params.get("date_to"):
            qs = qs.filter(created_at__date__lte=params["date_to"])
        if params.get("target_type"):
            qs = qs.filter(content_type__model=params["target_type"])
        if params.get("target_id"):
            qs = qs.filter(object_id=params["target_id"])

        return qs

    @extend_schema(
        summary="Export the filtered audit log as CSV",
        parameters=[
            OpenApiParameter(name="workspace", type=str, required=False),
            OpenApiParameter(name="action", type=str, required=False),
            OpenApiParameter(name="actor", type=str, required=False),
            OpenApiParameter(name="date_from", type=str, required=False),
            OpenApiParameter(name="date_to", type=str, required=False),
        ],
        responses={(200, "text/csv"): str},
    )
    @action(detail=False, methods=["get"])
    def export(self, request):
        """GET /activities/export/ — the current filter set as a CSV download."""
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="audit-log.csv"'

        writer = csv.writer(response)
        writer.writerow(
            ["timestamp", "actor", "action", "target_type", "target_id", "metadata"]
        )
        for activity in self.get_queryset()[:EXPORT_LIMIT]:
            writer.writerow(
                [
                    activity.created_at.isoformat(),
                    (
                        activity.actor.name or activity.actor.email
                        if activity.actor
                        else ""
                    ),
                    activity.action,
                    activity.content_type.model if activity.content_type else "",
                    activity.object_id or "",
                    activity.metadata,
                ]
            )
        return response
