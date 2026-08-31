"""
ASGI entrypoint.

Ordinary HTTP is handed to Django unchanged; ``/ws/`` routes go to Channels.
Serve this with an ASGI server (daphne, or gunicorn with uvicorn workers) --
under plain WSGI the REST API still works and only websockets are missing,
which the frontend handles by falling back to polling.

For more information, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

# Must be built before importing anything that touches models: it populates the
# app registry.
django_asgi_application = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.security.websocket import OriginValidator  # noqa: E402
from django.conf import settings  # noqa: E402

from apps.common.channels_auth import JWTAuthMiddleware  # noqa: E402
from apps.notifications.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_application,
        # Reject sockets opened from an origin we don't serve, so another site
        # cannot open an authenticated socket on a visitor's behalf. A missing
        # Origin header is refused too; browsers always send one.
        #
        # Checked against CORS_ALLOWED_ORIGINS rather than ALLOWED_HOSTS (what
        # AllowedHostsOriginValidator would use): the Origin here is the
        # *frontend's*, and ALLOWED_HOSTS lists the API's own hostnames. Those
        # coincide only while both run on localhost -- split them across
        # api.example.com and app.example.com and every socket would be denied.
        "websocket": OriginValidator(
            JWTAuthMiddleware(URLRouter(websocket_urlpatterns)),
            settings.CORS_ALLOWED_ORIGINS,
        ),
    }
)
