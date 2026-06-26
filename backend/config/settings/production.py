"""Production settings.

All sensitive values must be supplied via the environment. ``DEBUG`` defaults
to False (inherited from base) and is never turned on here.
"""

from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False

# Must be provided explicitly in production.
ALLOWED_HOSTS = env("ALLOWED_HOSTS")
CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")

# JSON-only API in production (no browsable API).
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = (  # noqa: F405
    "rest_framework.renderers.JSONRenderer",
)

# ---------------------------------------------------------------------------
# Security hardening
# ---------------------------------------------------------------------------
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=60 * 60 * 24 * 30)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
