from drf_spectacular.utils import extend_schema

from apps.common.viewsets import WorkspaceScopedViewSet
from apps.tasks.filters import TaskFilter
from apps.tasks.models import Task
from apps.tasks.serializers import TaskSerializer


@extend_schema(tags=["tasks"])
class TaskViewSet(WorkspaceScopedViewSet):
    queryset = Task.objects.select_related(
        "workspace", "project", "assignee", "reporter", "created_by", "updated_by"
    )
    serializer_class = TaskSerializer
    filterset_class = TaskFilter
    search_fields = ("title", "description")
    ordering_fields = (
        "created_at",
        "updated_at",
        "due_date",
        "priority",
        "status",
        "title",
    )
    ordering = ("-created_at",)
