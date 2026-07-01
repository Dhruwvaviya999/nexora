"""Mention API — read-only list of the current user's mentions."""

from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.mentions.models import Mention
from apps.mentions.serializers import MentionSerializer


@extend_schema(tags=["mentions"])
class MentionViewSet(viewsets.ReadOnlyModelViewSet):
    """Mentions where the current user is the mentioned party.

    Optional ``?workspace=<id>`` filter. The user-facing notification feed is
    built on top of this (and the ``user_mentioned`` signal) in the
    notifications phase.
    """

    serializer_class = MentionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Mention.objects.none()

        qs = Mention.objects.filter(
            mentioned_user=self.request.user
        ).select_related("comment", "comment__author", "mentioned_user", "workspace")

        workspace = self.request.query_params.get("workspace")
        if workspace:
            qs = qs.filter(workspace_id=workspace)

        return qs
