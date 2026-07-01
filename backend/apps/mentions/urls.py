"""Mention routes, mounted under /api/v1/mentions/."""

from rest_framework.routers import DefaultRouter

from apps.mentions.views import MentionViewSet

app_name = "mentions"

router = DefaultRouter()
router.register("", MentionViewSet, basename="mention")

urlpatterns = router.urls
