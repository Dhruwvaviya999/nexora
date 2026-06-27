"""Activity feed API (read-only) — powers workspace/project/task timelines."""

from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.activities.models import Activity
from apps.activities.serializers import ActivitySerializer


@extend_schema(tags=["activities"])
class ActivityViewSet(viewsets.ReadOnlyModelViewSet):
    """Activity scoped to the user's workspaces.

    Filters: ``?workspace=<id>``, ``?action=task.created``,
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
        if params.get("target_type"):
            qs = qs.filter(content_type__model=params["target_type"])
        if params.get("target_id"):
            qs = qs.filter(object_id=params["target_id"])

        return qs
