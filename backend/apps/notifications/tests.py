"""
Realtime notification tests.

Covers the websocket consumer directly (auth, isolation, push) and the service
that feeds it. The socket carries other people's messages, so who is allowed to
receive what is the part worth testing hardest.
"""

from __future__ import annotations

import logging

from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import TestCase, TransactionTestCase, override_settings
from rest_framework_simplejwt.tokens import RefreshToken

from apps.notifications.consumers import CLOSE_UNAUTHENTICATED, user_group
from apps.notifications.models import Notification, NotificationType
from apps.notifications.services import create_notification
from apps.workspaces.models import Workspace

User = get_user_model()

PWD = "Str0ng!Passw0rd"

IN_MEMORY_LAYER = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}

# Must match config.settings.test.CORS_ALLOWED_ORIGINS: the websocket origin
# validator is handed that list when config.asgi is imported.
ALLOWED_ORIGIN = "http://localhost:3000"


def access_token_for(user) -> str:
    return str(RefreshToken.for_user(user).access_token)


@override_settings(CHANNEL_LAYERS=IN_MEMORY_LAYER)
class NotificationConsumerTests(TransactionTestCase):
    """``/ws/notifications/`` -- authentication and delivery."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="socket@example.com", password=PWD, name="Socket User"
        )
        self.other = User.objects.create_user(
            email="other@example.com", password=PWD, name="Other User"
        )

    async def connect(self, token=None, origin=ALLOWED_ORIGIN):
        # Imported here so the ASGI application is built after the app registry
        # is ready, which is what config.asgi guarantees.
        from config.asgi import application

        url = "/ws/notifications/"
        if token:
            url = f"{url}?token={token}"
        # A browser always sends Origin, and the validator requires it.
        headers = [(b"origin", origin.encode())] if origin else []
        communicator = WebsocketCommunicator(application, url, headers=headers)
        connected, detail = await communicator.connect()
        return communicator, connected, detail

    async def test_a_valid_token_connects(self):
        token = await database_sync_to_async(access_token_for)(self.user)
        communicator, connected, _ = await self.connect(token)

        self.assertTrue(connected)
        greeting = await communicator.receive_json_from()
        self.assertEqual(greeting["type"], "connected")
        await communicator.disconnect()

    async def test_no_token_is_refused(self):
        communicator, connected, detail = await self.connect()

        self.assertFalse(connected)
        self.assertEqual(detail, CLOSE_UNAUTHENTICATED)
        await communicator.disconnect()

    async def test_a_garbage_token_is_refused(self):
        communicator, connected, detail = await self.connect("not-a-real-token")

        self.assertFalse(connected)
        self.assertEqual(detail, CLOSE_UNAUTHENTICATED)
        await communicator.disconnect()

    async def test_a_connection_from_another_origin_is_refused(self):
        """Otherwise any site could open a socket on a visitor's behalf."""
        token = await database_sync_to_async(access_token_for)(self.user)
        communicator, connected, _ = await self.connect(
            token, origin="http://evil.example.com"
        )

        self.assertFalse(connected)
        await communicator.disconnect()

    async def test_a_connection_with_no_origin_is_refused(self):
        token = await database_sync_to_async(access_token_for)(self.user)
        communicator, connected, _ = await self.connect(token, origin=None)

        self.assertFalse(connected)
        await communicator.disconnect()

    async def test_a_pushed_notification_arrives(self):
        token = await database_sync_to_async(access_token_for)(self.user)
        communicator, connected, _ = await self.connect(token)
        self.assertTrue(connected)
        await communicator.receive_json_from()  # the "connected" greeting

        from channels.layers import get_channel_layer

        layer = get_channel_layer()
        await layer.group_send(
            user_group(self.user.pk),
            {"type": "notification.created", "data": {"title": "Ping"}},
        )

        message = await communicator.receive_json_from()
        self.assertEqual(message["type"], "notification")
        self.assertEqual(message["notification"]["title"], "Ping")
        await communicator.disconnect()

    async def test_one_user_never_receives_anothers_notifications(self):
        token = await database_sync_to_async(access_token_for)(self.user)
        communicator, connected, _ = await self.connect(token)
        self.assertTrue(connected)
        await communicator.receive_json_from()

        from channels.layers import get_channel_layer

        await get_channel_layer().group_send(
            user_group(self.other.pk),
            {"type": "notification.created", "data": {"title": "Not yours"}},
        )

        self.assertTrue(
            await communicator.receive_nothing(timeout=0.3),
            "a notification leaked across users",
        )
        await communicator.disconnect()

    async def test_ping_is_answered(self):
        token = await database_sync_to_async(access_token_for)(self.user)
        communicator, connected, _ = await self.connect(token)
        await communicator.receive_json_from()

        await communicator.send_json_to({"type": "ping"})

        self.assertEqual((await communicator.receive_json_from())["type"], "pong")
        await communicator.disconnect()


@override_settings(CHANNEL_LAYERS=IN_MEMORY_LAYER)
class NotificationServiceTests(TestCase):
    """create_notification: rows, self-notification, and the realtime push."""

    def setUp(self):
        self.actor = User.objects.create_user(
            email="actor@example.com", password=PWD, name="Actor"
        )
        self.recipient = User.objects.create_user(
            email="recipient@example.com", password=PWD, name="Recipient"
        )
        self.workspace = Workspace.objects.create(name="WS", owner=self.actor)

    def test_a_notification_is_created(self):
        with self.captureOnCommitCallbacks(execute=True):
            notification = create_notification(
                recipient=self.recipient,
                actor=self.actor,
                workspace=self.workspace,
                type=NotificationType.MENTION,
                title="You were mentioned",
            )

        self.assertIsNotNone(notification)
        self.assertEqual(Notification.objects.count(), 1)

    def test_users_are_not_notified_about_their_own_actions(self):
        result = create_notification(
            recipient=self.actor,
            actor=self.actor,
            workspace=self.workspace,
            type=NotificationType.MENTION,
            title="Self mention",
        )

        self.assertIsNone(result)
        self.assertEqual(Notification.objects.count(), 0)

    def test_the_push_is_deferred_until_the_transaction_commits(self):
        """Pushing mid-transaction can outrun the write it describes."""
        # The captured list is filled as the block exits, so it is read after.
        with self.captureOnCommitCallbacks() as callbacks:
            create_notification(
                recipient=self.recipient,
                actor=self.actor,
                workspace=self.workspace,
                type=NotificationType.MENTION,
                title="Deferred",
            )

        self.assertEqual(
            len(callbacks), 1, "the realtime push was not deferred to on_commit"
        )

    def test_a_broken_channel_layer_does_not_break_the_write(self):
        # The point of the test is that the failure is swallowed, so keep the
        # resulting connection-error traceback out of the test output.
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)

        with override_settings(
            CHANNEL_LAYERS={
                "default": {
                    "BACKEND": "channels_redis.core.RedisChannelLayer",
                    # Nothing listens on this port.
                    "CONFIG": {"hosts": ["redis://127.0.0.1:65535"]},
                }
            }
        ):
            with self.captureOnCommitCallbacks(execute=True):
                notification = create_notification(
                    recipient=self.recipient,
                    actor=self.actor,
                    workspace=self.workspace,
                    type=NotificationType.MENTION,
                    title="Realtime is down",
                )

        self.assertIsNotNone(notification)
        self.assertEqual(Notification.objects.count(), 1)
