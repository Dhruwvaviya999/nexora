"""
Project package.

Importing the Celery app here guarantees it exists before any module reaches
for ``@shared_task``, which is what binds those tasks to this configuration.
"""

from config.celery import app as celery_app

__all__ = ("celery_app",)
