# syntax=docker/dockerfile:1
#
# Backend image. The same image runs the web process and the Celery worker --
# they differ only in the command, which keeps their code and dependencies
# identical by construction.

FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# libpq for psycopg, curl for the healthcheck. build-essential is only needed
# while compiling wheels, so it is removed in the same layer.
RUN apt-get update && apt-get install --no-install-recommends -y \
        libpq5 \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencies are copied on their own so an application change does not
# invalidate the (slow, torch-sized) dependency layer.
COPY requirements.txt .
RUN apt-get update \
    && apt-get install --no-install-recommends -y build-essential libpq-dev \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y --auto-remove build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY . .

# Run as a non-root user. Media and static are created up front so the volume
# mounts inherit the right ownership.
RUN useradd --create-home --uid 1000 nexora \
    && mkdir -p /app/media /app/staticfiles \
    && chown -R nexora:nexora /app
USER nexora

EXPOSE 8000

# Uvicorn directly: an ASGI server is required for the websocket routes, and
# uvicorn manages its own worker processes. gunicorn's uvicorn.workers shim is
# deprecated upstream, so it is deliberately not used.
CMD ["uvicorn", "config.asgi:application", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "3"]
