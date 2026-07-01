"""Workspace routes, mounted under /api/v1/workspaces/."""

from rest_framework.routers import DefaultRouter

from apps.workspaces.views import WorkspaceViewSet

app_name = "workspaces"

router = DefaultRouter()
router.register("", WorkspaceViewSet, basename="workspace")

urlpatterns = router.urls
