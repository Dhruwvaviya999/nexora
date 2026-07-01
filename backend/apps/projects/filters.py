import django_filters

from apps.projects.models import Project


class ProjectFilter(django_filters.FilterSet):
    """Query params: ?workspace=&status=&archived=&owner="""

    class Meta:
        model = Project
        fields = {
            "workspace": ["exact"],
            "status": ["exact"],
            "archived": ["exact"],
            "owner": ["exact"],
        }
