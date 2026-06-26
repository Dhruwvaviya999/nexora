"""Core API views: service-level endpoints not tied to a domain model."""

from django.db import connection
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckView(APIView):
    """Liveness/readiness probe.

    Returns ``200`` with ``{"status": "ok"}`` when the service and its database
    connection are healthy, ``503`` otherwise. Public on purpose so uptime
    monitors and orchestrators can reach it without a token.
    """

    permission_classes = [AllowAny]
    authentication_classes: list = []

    @extend_schema(
        summary="Health check",
        description="Reports service and database health.",
        responses={200: None, 503: None},
        tags=["core"],
    )
    def get(self, request: Request) -> Response:
        database_ok = True
        try:
            connection.ensure_connection()
        except Exception:  # pragma: no cover - exercised only when DB is down
            database_ok = False

        payload = {
            "status": "ok" if database_ok else "degraded",
            "service": "ai-knowledge-workflow-assistant",
            "version": "v1",
            "database": "ok" if database_ok else "unavailable",
        }
        http_status = (
            status.HTTP_200_OK if database_ok else status.HTTP_503_SERVICE_UNAVAILABLE
        )
        return Response(payload, status=http_status)
