import django_filters

from apps.handovers.models import Handover


class HandoverFilter(django_filters.FilterSet):
    """Query params: ?workspace=&task=&project=&status=&from_user=&to_user="""

    project = django_filters.UUIDFilter(field_name="task__project_id")

    class Meta:
        model = Handover
        fields = {
            "workspace": ["exact"],
            "task": ["exact"],
            "status": ["exact"],
            "from_user": ["exact"],
            "to_user": ["exact"],
        }
