"""
JWT authentication for WebSocket connections.

The browser WebSocket API cannot set an Authorization header, so the access
token travels in the query string (``/ws/notifications/?token=<access>``) --
the standard workaround. That places the token in the URL, so it must never be
logged: the connection is over wss:// in production and the token is short
lived (15 minutes by default), which is what makes this acceptable.

Anonymous connections are not rejected here; the consumer decides, so it can
close with a meaningful code.
"""

from __future__ import annotations

from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser


@database_sync_to_async
def _user_from_token(raw_token: str):
    # Imported lazily: this module is loaded from asgi.py, which runs before
    # the app registry is fully populated.
    from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
    from rest_framework_simplejwt.authentication import JWTAuthentication

    authenticator = JWTAuthentication()
    try:
        validated = authenticator.get_validated_token(raw_token)
        return authenticator.get_user(validated)
    except (InvalidToken, TokenError, KeyError):
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """Populate ``scope["user"]`` from a ``token`` query parameter."""

    async def __call__(self, scope, receive, send):
        query = parse_qs((scope.get("query_string") or b"").decode(errors="ignore"))
        tokens = query.get("token") or []

        scope["user"] = (
            await _user_from_token(tokens[0]) if tokens else AnonymousUser()
        )
        return await super().__call__(scope, receive, send)
