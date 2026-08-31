"""
Outgoing email.

One helper so every message the product sends is rendered, addressed and
failure-handled the same way. Templates live in ``templates/email/<name>.txt``
with an optional ``.html`` sibling.

Sending is best effort by default: an SMTP outage must not turn an invitation
or a password-reset request into a 500. Callers that genuinely depend on
delivery pass ``fail_silently=False``.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def frontend_url(path: str = "") -> str:
    """Absolute URL into the Next.js app."""
    return f"{settings.FRONTEND_URL}/{path.lstrip('/')}" if path else settings.FRONTEND_URL


def send_templated_email(
    *,
    template: str,
    subject: str,
    to: list[str] | str,
    context: dict | None = None,
    fail_silently: bool = True,
) -> int:
    """Render ``email/<template>.txt`` (+ ``.html``) and send it.

    Returns the number of messages sent (0 on failure when failing silently).
    """
    recipients = [to] if isinstance(to, str) else list(to)
    recipients = [address for address in recipients if address]
    if not recipients:
        return 0

    ctx = {"frontend_url": settings.FRONTEND_URL, **(context or {})}
    body = render_to_string(f"email/{template}.txt", ctx).strip() + "\n"

    message = EmailMultiAlternatives(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipients,
    )

    try:
        html = render_to_string(f"email/{template}.html", ctx)
    except TemplateDoesNotExist:
        html = None
    if html:
        message.attach_alternative(html, "text/html")

    try:
        return message.send(fail_silently=False)
    except Exception:  # noqa: BLE001 -- delivery must not break the request
        if not fail_silently:
            raise
        logger.exception("Failed to send %r email to %s", template, recipients)
        return 0


def queue_templated_email(
    *, template: str, subject: str, to: list[str] | str, context: dict | None = None
) -> None:
    """Hand an email to a worker, after the current transaction commits.

    Queuing before the commit races the worker: it can pick the job up and mail
    a link to a row that is not visible yet, or to one that never lands because
    the transaction rolled back. With CELERY_TASK_ALWAYS_EAGER (development,
    tests) this still runs inline -- just at commit time rather than mid-write.
    """
    from apps.common.tasks import send_email_task

    payload = {
        "template": template,
        "subject": subject,
        "to": [to] if isinstance(to, str) else list(to),
        "context": context or {},
    }

    def dispatch():
        try:
            send_email_task.delay(**payload)
        except Exception:  # noqa: BLE001 -- an unreachable broker is not fatal
            logger.exception("Could not queue %r email; sending inline", template)
            send_templated_email(**payload)

    transaction.on_commit(dispatch)
