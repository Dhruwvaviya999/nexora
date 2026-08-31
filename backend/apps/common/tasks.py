"""
Shared background tasks.

Sending mail over SMTP costs a network round trip and can hang for as long as
EMAIL_TIMEOUT. Doing that inside a request makes signing up or inviting someone
feel broken, so delivery is handed to a worker and retried on failure.
"""

from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    # 30s, then 60s, then 120s.
    default_retry_delay=30,
    retry_backoff=True,
    ignore_result=True,
)
def send_email_task(self, *, template: str, subject: str, to, context: dict | None = None):
    """Render and send one templated email, retrying transient SMTP failures."""
    # Imported here so the module can be loaded by the worker without pulling
    # Django's mail machinery in at import time.
    from apps.common.email import send_templated_email

    try:
        return send_templated_email(
            template=template,
            subject=subject,
            to=to,
            context=context,
            # Raise so Celery sees the failure and can retry it.
            fail_silently=False,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Email %r to %s failed (attempt %s/%s)",
            template,
            to,
            self.request.retries + 1,
            self.max_retries + 1,
        )
        raise self.retry(exc=exc)
