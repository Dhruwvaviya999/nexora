"""Notification API: the current user's notification feed + read actions."""

from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.notifications.models import Notification
from apps.notifications.serializers import NotificationSerializer


@extend_schema(tags=["notifications"])
class NotificationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Read the current user's notifications and mark them read.

    Supports ``?is_read=true|false``, ``?type=<type>`` and ``?workspace=<id>``.
    """

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Notification.objects.none()

        qs = Notification.objects.filter(
            recipient=self.request.user
        ).select_related("actor")

        params = self.request.query_params
        is_read = params.get("is_read")
        if is_read in ("true", "false"):
            qs = qs.filter(is_read=(is_read == "true"))
        if params.get("type"):
            qs = qs.filter(type=params["type"])
        if params.get("workspace"):
            qs = qs.filter(workspace_id=params["workspace"])

        return qs

    @extend_schema(responses={200: {"type": "object", "properties": {"count": {"type": "integer"}}}})
    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        count = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).count()
        return Response({"count": count})

    @action(detail=True, methods=["patch"])
    def read(self, request, pk=None):
        notification = self.get_object()
        if not notification.is_read:
            notification.is_read = True
            notification.save(update_fields=["is_read", "updated_at"])
        return Response(self.get_serializer(notification).data)

    @extend_schema(request=None, responses={200: {"type": "object", "properties": {"updated": {"type": "integer"}}}})
    @action(detail=False, methods=["patch"], url_path="read-all")
    def read_all(self, request):
        updated = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).update(is_read=True)
        return Response({"updated": updated}, status=status.HTTP_200_OK)
