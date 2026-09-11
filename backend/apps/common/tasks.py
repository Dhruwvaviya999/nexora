"""
Shared background tasks.

Two kinds live here:

* **Outgoing email.** Sending over SMTP costs a network round trip and can hang
  for as long as EMAIL_TIMEOUT. Doing that inside a request makes signing up or
  inviting someone feel broken, so delivery is handed to a worker and retried.

* **Periodic maintenance.** Several tables grow without bound unless something
  prunes them; the schedule lives in ``CELERY_BEAT_SCHEDULE``. Each task is
  named explicitly so the schedule refers to a stable string rather than a
  module path that a refactor could move.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from io import StringIO

from celery import shared_task
from django.core.management import call_command
from django.utils import timezone

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


# ---------------------------------------------------------------------------
# Periodic maintenance
# ---------------------------------------------------------------------------
# Scheduled from CELERY_BEAT_SCHEDULE. All of these are idempotent and safe to
# run more than once, so a missed or duplicated beat tick costs nothing.


@shared_task(name="common.flush_expired_tokens", ignore_result=True)
def flush_expired_tokens() -> str:
    """Delete JWT rows whose expiry has passed.

    ``ROTATE_REFRESH_TOKENS`` writes one OutstandingToken per refresh, so an
    active user generates hundreds of rows a week -- and the blacklist is
    consulted on every token validation. SimpleJWT ships the command; nothing
    was scheduling it.
    """
    out = StringIO()
    call_command("flushexpiredtokens", stdout=out)
    logger.info("flushexpiredtokens: %s", out.getvalue().strip() or "done")
    return "ok"


@shared_task(name="common.expire_stale_invitations", ignore_result=True)
def expire_stale_invitations() -> int:
    """Mark past-due pending invitations as expired.

    Expiry is otherwise lazy -- the status only flips when someone tries to
    accept -- so "pending invitations" counts drift upward over time.
    """
    from apps.invitations.models import Invitation, InvitationStatus

    updated = Invitation.objects.filter(
        status=InvitationStatus.PENDING, expires_at__lt=timezone.now()
    ).update(status=InvitationStatus.EXPIRED, updated_at=timezone.now())
    if updated:
        logger.info("Expired %s stale invitation(s)", updated)
    return updated


@shared_task(name="common.prune_embedding_jobs", ignore_result=True)
def prune_embedding_jobs(days: int = 30) -> int:
    """Drop finished embedding jobs older than ``days``.

    Jobs are an operational log, not domain data: the document keeps its
    chunks. Unfinished jobs are left alone so a stuck one stays visible.
    """
    from apps.knowledge.models import EmbeddingJob, EmbeddingStatus

    cutoff = timezone.now() - timedelta(days=days)
    deleted, _ = EmbeddingJob.objects.filter(
        created_at__lt=cutoff,
        status__in=(EmbeddingStatus.COMPLETED, EmbeddingStatus.FAILED),
    ).delete()
    if deleted:
        logger.info("Pruned %s embedding job(s) older than %s days", deleted, days)
    return deleted


@shared_task(name="common.prune_search_history", ignore_result=True)
def prune_search_history(days: int = 90) -> int:
    """Drop search history older than ``days``.

    These rows store raw user query text, so retaining them indefinitely is a
    privacy cost with no product benefit past the "recent queries" window.
    """
    from apps.ai.models import SearchHistory

    cutoff = timezone.now() - timedelta(days=days)
    deleted, _ = SearchHistory.objects.filter(created_at__lt=cutoff).delete()
    if deleted:
        logger.info("Pruned %s search history row(s) older than %s days", deleted, days)
    return deleted
