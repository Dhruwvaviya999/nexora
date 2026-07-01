"""Local development settings."""

from .base import *  # noqa: F401,F403
from .base import env

# Default to DEBUG on locally even if .env omits it.
DEBUG = env("DEBUG", default=True)

ALLOWED_HOSTS = env("ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "0.0.0.0"])

# Permissive CORS for local frontends (Next.js dev server on :3000).
CORS_ALLOWED_ORIGINS = env(
    "CORS_ALLOWED_ORIGINS",
    default=["http://localhost:3000", "http://127.0.0.1:3000"],
)

# Browsable API is handy during development.
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = (  # noqa: F405
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
)
