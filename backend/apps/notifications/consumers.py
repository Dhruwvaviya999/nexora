"""
WebSocket consumer that pushes notifications to their recipient.

Each authenticated connection joins a group private to that user, so a
notification created anywhere -- a web request, a Celery worker -- reaches
every device that user has open, and only that user.

The socket is push-only. Marking things read still goes through the REST API,
which keeps one code path for permissions and auditing.
"""

from __future__ import annotations

import logging

from asgiref.sync import async_to_sync
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)

# WebSocket close codes (4000+ is the application-defined range).
CLOSE_UNAUTHENTICATED = 4401


def user_group(user_id) -> str:
    """Channel group carrying one user's notifications."""
    # Group names allow only alphanumerics, hyphens, underscores and periods.
    return f"notifications.{str(user_id).replace('-', '')}"


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    """``/ws/notifications/?token=<access token>``"""

    async def connect(self):
        user = self.scope.get("user")
        if user is None or not user.is_authenticated:
            # Accept-then-close would look like success to the client; refuse.
            await self.close(code=CLOSE_UNAUTHENTICATED)
            return

        self.group_name = user_group(user.pk)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_json({"type": "connected"})

    async def disconnect(self, code):
        group_name = getattr(self, "group_name", None)
        if group_name:
            await self.channel_layer.group_discard(group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        # Push-only, but answer pings so clients can keep the socket warm
        # through proxies that cut idle connections.
        if isinstance(content, dict) and content.get("type") == "ping":
            await self.send_json({"type": "pong"})

    # -- messages pushed from the channel layer -------------------------
    async def notification_created(self, event):
        await self.send_json({"type": "notification", "notification": event["data"]})

    async def unread_count(self, event):
        await self.send_json({"type": "unread_count", "count": event["count"]})


def push_to_user(user_id, message: dict) -> None:
    """Send ``message`` to every socket held by ``user_id``.

    Safe to call from synchronous code (signals, views, Celery tasks). Realtime
    delivery is a convenience on top of the REST API -- the frontend also polls
    -- so a channel layer that is down must never break the write that
    triggered it.
    """
    try:
        channel_layer = get_channel_layer()
        if channel_layer is None:
            return
        async_to_sync(channel_layer.group_send)(user_group(user_id), message)
    except Exception:  # noqa: BLE001 -- realtime is best effort
        logger.warning("Could not push realtime message to user %s", user_id, exc_info=True)
