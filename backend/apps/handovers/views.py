from django.http import HttpResponse
from django.utils import timezone
from django.utils.text import slugify
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.common.viewsets import WorkspaceScopedViewSet
from apps.handovers.filters import HandoverFilter
from apps.handovers.models import Handover, HandoverStatus
from apps.handovers.serializers import HandoverReviewSerializer, HandoverSerializer
from apps.notifications.models import NotificationType
from apps.notifications.services import create_notification
from apps.workspaces.models import REVIEWER_ROLES


def _display(user) -> str:
    return user.name or user.email


@extend_schema(tags=["handovers"])
class HandoverViewSet(WorkspaceScopedViewSet):
    queryset = Handover.objects.select_related(
        "workspace",
        "task",
        "task__project",
        "from_user",
        "to_user",
        "reviewer",
        "created_by",
        "updated_by",
    )
    serializer_class = HandoverSerializer
    filterset_class = HandoverFilter
    search_fields = ("summary", "pending_items", "task__title")
    ordering_fields = ("created_at", "updated_at", "status", "reviewed_at")
    ordering = ("-created_at",)

    def _reviewer_membership(self, workspace):
        """Return the requesting user's membership if it carries review rights."""
        member = workspace.members.filter(user=self.request.user).first()
        if member is None or member.role not in REVIEWER_ROLES:
            return None
        return member

    def perform_create(self, serializer):
        super().perform_create(serializer)
        handover = serializer.instance
        create_notification(
            recipient=handover.to_user,
            actor=handover.from_user,
            workspace=handover.workspace,
            type=NotificationType.HANDOVER_SUBMITTED,
            title=f"{_display(handover.from_user)} handed over “{handover.task.title}”",
            message=(handover.summary or "")[:140],
            link=f"/handovers/{handover.pk}",
        )

    def perform_update(self, serializer):
        handover = self.get_object()
        if handover.from_user_id != self.request.user.pk:
            raise PermissionDenied("Only the submitter can edit a handover.")
        super().perform_update(serializer)

    def perform_destroy(self, instance):
        if instance.status != HandoverStatus.PENDING:
            raise ValidationError("Only pending handovers can be deleted.")
        is_submitter = instance.from_user_id == self.request.user.pk
        if not is_submitter and self._reviewer_membership(instance.workspace) is None:
            raise PermissionDenied(
                "Only the submitter or a workspace manager can delete a handover."
            )
        instance.delete()

    @extend_schema(request=HandoverReviewSerializer, responses=HandoverSerializer)
    @action(detail=True, methods=["post"])
    def review(self, request, pk=None):
        """POST /handovers/{id}/review/ — approve or reject a pending handover.

        Owners, admins, and managers only. Approving reassigns the task to the
        recipient; rejecting leaves the task untouched and returns the handover
        to the submitter with a comment.
        """
        handover = self.get_object()

        if self._reviewer_membership(handover.workspace) is None:
            raise PermissionDenied(
                "Only workspace owners, admins, and managers can review handovers."
            )
        if handover.status != HandoverStatus.PENDING:
            raise ValidationError("This handover has already been reviewed.")

        input_serializer = HandoverReviewSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        decision = input_serializer.validated_data["decision"]
        comment = input_serializer.validated_data.get("comment", "")

        handover.status = decision
        handover.reviewer = request.user
        handover.review_comment = comment
        handover.reviewed_at = timezone.now()
        handover.updated_by = request.user
        handover.save(
            update_fields=[
                "status",
                "reviewer",
                "review_comment",
                "reviewed_at",
                "updated_by",
                "updated_at",
            ]
        )

        approved = decision == HandoverStatus.APPROVED
        if approved and handover.to_user is not None:
            task = handover.task
            task.assignee = handover.to_user
            task.updated_by = request.user
            task.save(update_fields=["assignee", "updated_by", "updated_at"])
            create_notification(
                recipient=handover.to_user,
                actor=request.user,
                workspace=handover.workspace,
                type=NotificationType.TASK_ASSIGNED,
                title=f"“{task.title}” is now assigned to you",
                message="A handover to you was approved.",
                link=f"/tasks/{task.pk}",
            )

        create_notification(
            recipient=handover.from_user,
            actor=request.user,
            workspace=handover.workspace,
            type=NotificationType.HANDOVER_REVIEWED,
            title=(
                f"Your handover of “{handover.task.title}” was "
                f"{'approved' if approved else 'rejected'}"
            ),
            message=(comment or "")[:140],
            link=f"/handovers/{handover.pk}",
        )

        return Response(self.get_serializer(handover).data)

    @extend_schema(
        summary="Export the handover as a PDF",
        responses={(200, "application/pdf"): bytes},
    )
    @action(detail=True, methods=["get"])
    def export(self, request, pk=None):
        """GET /handovers/{id}/export/ — printable PDF record of the handover."""
        # Local import so the app works even before reportlab is installed.
        from apps.handovers.pdf import render_handover_pdf

        handover = self.get_object()
        pdf = render_handover_pdf(handover)
        filename = f"handover-{slugify(handover.task.title) or handover.pk}.pdf"
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
