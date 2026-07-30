"""URL routes for the core app (mounted under /api/v1/)."""

from django.urls import path

from apps.core.views import AnalyticsView, DashboardView, HealthCheckView

app_name = "core"

urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="health"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("analytics/", AnalyticsView.as_view(), name="analytics"),
]
