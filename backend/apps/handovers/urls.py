from rest_framework.routers import DefaultRouter

from apps.handovers.views import HandoverViewSet

app_name = "handovers"

router = DefaultRouter()
router.register("", HandoverViewSet, basename="handover")

urlpatterns = router.urls
