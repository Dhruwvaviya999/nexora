"""
Root URL configuration.

API routes are versioned under ``/api/v1/``. Each version delegates to the
included app URLConfs so new versions can be added side-by-side later.
"""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

api_v1_patterns = [
    path("", include("apps.core.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    # Versioned API
    path("api/v1/", include((api_v1_patterns, "v1"), namespace="v1")),
    # OpenAPI schema & docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]
