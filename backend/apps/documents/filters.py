import django_filters

from apps.documents.models import Document


class DocumentFilter(django_filters.FilterSet):
    """Query params: ?workspace=&project=&file_type="""

    class Meta:
        model = Document
        fields = {
            "workspace": ["exact"],
            "project": ["exact"],
            "file_type": ["exact", "icontains"],
        }
