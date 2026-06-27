"""Invitation routes, mounted under /api/v1/invitations/."""

from rest_framework.routers import DefaultRouter

from apps.invitations.views import InvitationViewSet

app_name = "invitations"

router = DefaultRouter()
router.register("", InvitationViewSet, basename="invitation")

urlpatterns = router.urls
