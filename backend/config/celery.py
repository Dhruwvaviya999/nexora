"""
Celery application.

Imported from ``config/__init__.py`` so that ``@shared_task`` in the apps binds
to this instance no matter how the process was started (web, worker, shell).

Run a worker with:

    celery -A config worker --loglevel=info
"""

from __future__ import annotations

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("nexora")

# All Celery settings live in Django settings under the CELERY_ prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Pick up tasks.py in every installed app.
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Trivial task for checking that a worker is alive and consuming."""
    return f"ok: {self.request.id}"
