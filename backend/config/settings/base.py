"""
Base settings shared across all environments.

Environment-specific overrides live in ``development.py`` and ``production.py``.
Secrets and per-machine values are read from the environment (a local ``.env``
file is loaded automatically) — never hard-code them here.
"""

from datetime import timedelta
from pathlib import Path

import environ

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
# BASE_DIR points at the ``backend/`` directory (two parents up from this file:
# config/settings/base.py -> config -> backend).
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ---------------------------------------------------------------------------
# Environment variables (django-environ)
# ---------------------------------------------------------------------------
env = environ.Env(
    DEBUG=(bool, False),
    SECRET_KEY=(str, ""),
    ALLOWED_HOSTS=(list, []),
    CORS_ALLOWED_ORIGINS=(list, []),
)

# Load a .env file if present (no-op in environments that inject real env vars).
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    # daphne must precede django.contrib.staticfiles: it replaces `runserver`
    # with an ASGI-aware one so websockets work in development too.
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "channels",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
]

# First-party apps live under the ``apps/`` package.
LOCAL_APPS = [
    "apps.common",
    "apps.core",
    "apps.accounts",
    "apps.workspaces",
    "apps.projects",
    "apps.tasks",
    "apps.handovers",
    "apps.documents",
    "apps.comments",
    "apps.mentions",
    "apps.notifications",
    "apps.activities",
    "apps.invitations",
    # Phase 5 — AI Knowledge Assistant
    "apps.knowledge",
    "apps.ai",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # CorsMiddleware must sit as high as possible, before CommonMiddleware.
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # Project-wide templates (email bodies live in templates/email/).
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
    # Plain-text templates: HTML autoescaping must be off.
    #
    # With it on, an "&" in a URL renders as "&amp;", so a password-reset link
    # in a text email arrives carrying a parameter literally named "amp;token"
    # and the reset silently fails. A dedicated engine fixes that for every text
    # template at once, instead of each one having to remember
    # {% autoescape off %}. Selected by name: render_to_string(..., using="text").
    #
    # It must come *after* the default engine: django.contrib.admin's system
    # checks inspect the first DjangoTemplates engine for the auth and messages
    # context processors, and would fail against this one.
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "NAME": "text",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {"autoescape": False},
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---------------------------------------------------------------------------
# Database (PostgreSQL via DATABASE_URL)
# ---------------------------------------------------------------------------
# A single Postgres database, configured from a DATABASE_URL connection string,
# e.g. postgres://user:pass@localhost:5432/nexora
DATABASES = {
    "default": env.db("DATABASE_URL"),
}

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
# Custom user model set up at project start so it can be extended in future
# phases without a painful migration. No auth *logic* is implemented yet.
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static & media files
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # --- Rate limiting -----------------------------------------------------
    # Anonymous traffic is keyed by IP, authenticated traffic by user id. The
    # scoped rates below protect the endpoints worth attacking; see
    # apps.common.throttling for the named scopes.
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": env("THROTTLE_ANON", default="60/min"),
        "user": env("THROTTLE_USER", default="1000/hour"),
        # Credential endpoints: brute-force surface, deliberately tight.
        "login": env("THROTTLE_LOGIN", default="10/min"),
        "register": env("THROTTLE_REGISTER", default="5/hour"),
        # Password reset also *sends mail*, so it is an abuse vector twice over.
        "password_reset": env("THROTTLE_PASSWORD_RESET", default="5/hour"),
        # LLM calls cost money per request.
        "ai": env("THROTTLE_AI", default="30/hour"),
    },
}

# ---------------------------------------------------------------------------
# Caching
# ---------------------------------------------------------------------------
# DRF throttling counts requests in the cache. The default per-process
# LocMemCache would give each gunicorn worker its own private counter, so the
# effective limit becomes rate x worker_count. Redis makes it shared and real.
REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("CACHE_URL", default=REDIS_URL),
    }
}

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
# Development overrides this with the console backend; production must supply
# real SMTP credentials. Anything user-facing that leaves the system (invites,
# password resets) goes through apps.common.email.
EMAIL_BACKEND = env(
    "EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend"
)
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_TIMEOUT = env.int("EMAIL_TIMEOUT", default=10)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Nexora <no-reply@nexora.app>")

# Public base URL of the Next.js app. Every link in an outgoing email is built
# from this, so it must be the address recipients can actually reach.
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:3000").rstrip("/")

# How long a password-reset link stays valid.
PASSWORD_RESET_TIMEOUT = env.int("PASSWORD_RESET_TIMEOUT", default=60 * 60 * 24)

# ---------------------------------------------------------------------------
# Celery (background jobs)
# ---------------------------------------------------------------------------
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default=REDIS_URL)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
# Fail loudly rather than hanging a web request when the broker is unreachable.
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_TRANSPORT_OPTIONS = {"max_retries": 3}
# One task at a time per worker process: embedding is CPU-bound and holds a
# multi-hundred-megabyte model in memory.
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_ACKS_LATE = True
# Embedding a large PDF is slow, but not unbounded.
CELERY_TASK_SOFT_TIME_LIMIT = env.int("CELERY_TASK_SOFT_TIME_LIMIT", default=600)
CELERY_TASK_TIME_LIMIT = env.int("CELERY_TASK_TIME_LIMIT", default=660)
# Run inline when no worker is available (development, tests, CI).
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=False)
CELERY_TASK_EAGER_PROPAGATES = False

# ---------------------------------------------------------------------------
# Channels (realtime)
# ---------------------------------------------------------------------------
# ASGI_APPLICATION is set above, next to WSGI_APPLICATION.
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [env("CHANNEL_LAYER_URL", default=REDIS_URL)]},
    }
}

# ---------------------------------------------------------------------------
# SimpleJWT (configuration only — endpoints arrive in Phase 2)
# ---------------------------------------------------------------------------
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=env.int("JWT_ACCESS_TOKEN_LIFETIME_MINUTES", default=15)
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=env.int("JWT_REFRESH_TOKEN_LIFETIME_DAYS", default=7)
    ),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    # SimpleJWT calls this SIGNING_KEY; it rejects "SECRET_KEY" outright, which
    # takes the whole app down at import time.
    # Falls back to SECRET_KEY when JWT_SIGNING_KEY is unset *or* blank.
    "SIGNING_KEY": env("JWT_SIGNING_KEY", default="") or SECRET_KEY,
}

# ---------------------------------------------------------------------------
# drf-spectacular (OpenAPI 3 schema)
# ---------------------------------------------------------------------------
SPECTACULAR_SETTINGS = {
    "TITLE": "AI Knowledge & Workflow Assistant API",
    "DESCRIPTION": "REST API for the AI Knowledge & Workflow Assistant platform.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": "/api/v[0-9]+",
}

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")

# ---------------------------------------------------------------------------
# AI / RAG (Phase 5)
# ---------------------------------------------------------------------------
# Central configuration for the AI Knowledge Assistant. Per-workspace overrides
# (provider, model, temperature, API key) live in apps.ai.models.AISettings and
# take precedence over these defaults at runtime.
#
# IMPORTANT: ``EMBEDDING_DIM`` is baked into the pgvector column at migration
# time. Changing it (e.g. switching to a 768/1536-dim provider) requires a new
# migration that alters the ``DocumentChunk.embedding`` column.
AI = {
    # --- LLM (chat / summaries / action items) ---
    "DEFAULT_LLM_PROVIDER": env("AI_LLM_PROVIDER", default="gemini"),
    "DEFAULT_CHAT_MODEL": env("AI_CHAT_MODEL", default="gemini-3.6-flash"),
    "DEFAULT_TEMPERATURE": env.float("AI_TEMPERATURE", default=0.2),
    "DEFAULT_MAX_TOKENS": env.int("AI_MAX_TOKENS", default=1024),
    # --- Embeddings (semantic search / retrieval) ---
    "DEFAULT_EMBEDDING_PROVIDER": env(
        "AI_EMBEDDING_PROVIDER", default="sentence_transformer"
    ),
    "DEFAULT_EMBEDDING_MODEL": env(
        "AI_EMBEDDING_MODEL", default="all-MiniLM-L6-v2"
    ),
    "EMBEDDING_DIM": 384,
    # --- Chunking ---
    "CHUNK_SIZE_WORDS": env.int("AI_CHUNK_SIZE_WORDS", default=220),
    "CHUNK_OVERLAP_WORDS": env.int("AI_CHUNK_OVERLAP_WORDS", default=40),
    "EMBED_BATCH_SIZE": env.int("AI_EMBED_BATCH_SIZE", default=32),
    # --- Retrieval ---
    "SEARCH_TOP_K": env.int("AI_SEARCH_TOP_K", default=6),
    # Cosine distance threshold above which a chunk is considered irrelevant
    # (distance is 0 = identical .. 2 = opposite; similarity = 1 - distance).
    "SEARCH_MAX_DISTANCE": env.float("AI_SEARCH_MAX_DISTANCE", default=0.75),
    # --- Provider API keys (fallbacks; per-workspace keys override these) ---
    "GEMINI_API_KEY": env("GEMINI_API_KEY", default=""),
    "OPENAI_API_KEY": env("OPENAI_API_KEY", default=""),
    "OLLAMA_BASE_URL": env("OLLAMA_BASE_URL", default="http://localhost:11434"),
    # --- Security ---
    # Fernet key for encrypting AISettings.api_key at rest. If unset, a key is
    # derived from SECRET_KEY (fine for dev; set a dedicated key in production).
    "FIELD_ENCRYPTION_KEY": env("AI_FIELD_ENCRYPTION_KEY", default=""),
    # Hard cap on user-supplied prompt length (prompt-injection / abuse guard).
    "MAX_INPUT_CHARS": env.int("AI_MAX_INPUT_CHARS", default=4000),
}
