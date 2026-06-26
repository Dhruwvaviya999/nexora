import django_filters

from apps.tasks.models import Task


class TaskFilter(django_filters.FilterSet):
    """Query params: ?workspace=&project=&status=&priority=&assignee=&due_before=&due_after="""

    due_before = django_filters.DateFilter(field_name="due_date", lookup_expr="lte")
    due_after = django_filters.DateFilter(field_name="due_date", lookup_expr="gte")

    class Meta:
        model = Task
        fields = {
            "workspace": ["exact"],
            "project": ["exact"],
            "status": ["exact"],
            "priority": ["exact"],
            "assignee": ["exact"],
        }
