from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.viewsets import WorkspaceScopedViewSet
from apps.projects.filters import ProjectFilter
from apps.projects.models import Project
from apps.projects.serializers import ProjectSerializer


@extend_schema(tags=["projects"])
class ProjectViewSet(WorkspaceScopedViewSet):
    queryset = Project.objects.select_related(
        "workspace", "owner", "created_by", "updated_by"
    )
    serializer_class = ProjectSerializer
    filterset_class = ProjectFilter
    search_fields = ("name", "description")
    ordering_fields = ("created_at", "updated_at", "name", "status")
    ordering = ("-created_at",)

    def _set_archived(self, request, archived: bool):
        project = self.get_object()
        project.archived = archived
        project.updated_by = request.user
        project.save(update_fields=["archived", "updated_by", "updated_at"])
        return Response(self.get_serializer(project).data)

    @extend_schema(request=None, responses=ProjectSerializer)
    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        return self._set_archived(request, True)

    @extend_schema(request=None, responses=ProjectSerializer)
    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):
        return self._set_archived(request, False)
