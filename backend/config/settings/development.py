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

# ---------------------------------------------------------------------------
# Infrastructure that development shouldn't require
# ---------------------------------------------------------------------------
# Nexora runs locally with nothing but Postgres. Redis, a Celery worker and an
# SMTP server are all optional here; each falls back to an in-process
# equivalent, and every one of them is switched on by simply setting the
# matching environment variable.

# Print emails to the console instead of sending them.
EMAIL_BACKEND = env(
    "EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)

# Run Celery tasks inline unless a broker is explicitly configured. Document
# uploads stay synchronous locally, exactly as they behaved before.
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=True)

# In-memory channel layer: websockets work with `runserver` and no Redis.
# It is per-process, so a multi-worker deploy must use the Redis layer.
if not env("CHANNEL_LAYER_URL", default=""):
    CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}

# Local-memory cache so throttling works without Redis. Single process in
# development, so the counters are still accurate.
if not env("CACHE_URL", default=""):
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "nexora-dev",
        }
    }
