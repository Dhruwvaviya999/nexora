"""Activity routes, mounted under /api/v1/activities/."""

from rest_framework.routers import DefaultRouter

from apps.activities.views import ActivityViewSet

app_name = "activities"

router = DefaultRouter()
router.register("", ActivityViewSet, basename="activity")

urlpatterns = router.urls
