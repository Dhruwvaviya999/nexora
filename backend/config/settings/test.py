"""
Settings for the test suite.

Tests must not depend on Redis, a Celery worker or an SMTP server being up, and
they must not be rate limited -- a test that walks 40 endpoints would otherwise
trip the throttles and fail for reasons that have nothing to do with the code
under test. `manage.py test` selects this module automatically.
"""

from .base import *  # noqa: F401,F403
from .base import REST_FRAMEWORK, env  # noqa: F401

DEBUG = False

ALLOWED_HOSTS = ["*", "testserver"]

# Pinned, not inherited from the environment. config.asgi hands this list to the
# websocket OriginValidator when it is imported, so override_settings cannot
# change it later -- the consumer tests connect with exactly this origin.
CORS_ALLOWED_ORIGINS = ["http://localhost:3000"]

# ---------------------------------------------------------------------------
# No external services
# ---------------------------------------------------------------------------
# Collect mail in django.core.mail.outbox so tests can assert on it.
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Tasks run inline, in-process, and re-raise so a broken task fails its test.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "nexora-test",
    }
}

# ---------------------------------------------------------------------------
# Throttling
# ---------------------------------------------------------------------------
# Off by default: a test that walks 40 endpoints is not an attack.
#
# Clearing DEFAULT_THROTTLE_CLASSES alone would not be enough -- the auth views
# name their throttles explicitly, which overrides the default. A rate of None
# is what actually disables a scope (SimpleRateThrottle.allow_request returns
# True immediately). Tests that exercise throttling patch these back in; see
# apps/accounts/tests.py.
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_THROTTLE_CLASSES": (),
    "DEFAULT_THROTTLE_RATES": {
        "anon": None,
        "user": None,
        "login": None,
        "register": None,
        "password_reset": None,
        "ai": None,
    },
}

# ---------------------------------------------------------------------------
# Speed
# ---------------------------------------------------------------------------
# The default PBKDF2 hasher is deliberately slow; the suite creates a lot of
# users and does not test hashing strength.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
