"""
Refresh-token cookie handling.

The refresh token is the long-lived credential (7 days by default), so it is
issued as an **httpOnly** cookie rather than returned in the JSON body: script
running on the page cannot read it, which means an XSS cannot exfiltrate a
week-long session. The access token stays in the JSON body and the client keeps
it in memory only, where it dies with the tab and expires in 15 minutes anyway.

Same-site notes
---------------
The cookie is set on the *API's* origin and travels back on credentialed
requests. ``localhost:3000`` -> ``localhost:8000`` and
``app.example.com`` -> ``api.example.com`` are both **same-site** (ports and
subdomains do not affect site), so the default ``Lax`` works for the normal
deployment shapes. A genuinely cross-site split needs
``AUTH_COOKIE_SAMESITE=None`` with ``AUTH_COOKIE_SECURE=True``.

The path is scoped to the auth routes so the cookie is not attached to every
API call -- only refresh and logout need it.
"""

from __future__ import annotations

from django.conf import settings


def cookie_name() -> str:
    return settings.AUTH_COOKIE_NAME


def set_refresh_cookie(response, refresh_token: str):
    """Attach the httpOnly refresh cookie to ``response``."""
    response.set_cookie(
        key=settings.AUTH_COOKIE_NAME,
        value=refresh_token,
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        path=settings.AUTH_COOKIE_PATH,
        domain=settings.AUTH_COOKIE_DOMAIN or None,
    )
    return response


def clear_refresh_cookie(response):
    """Remove the refresh cookie.

    ``delete_cookie`` has to be given the same path/domain/samesite it was set
    with, or the browser keeps the original cookie and logout silently fails.
    """
    response.delete_cookie(
        key=settings.AUTH_COOKIE_NAME,
        path=settings.AUTH_COOKIE_PATH,
        domain=settings.AUTH_COOKIE_DOMAIN or None,
        samesite=settings.AUTH_COOKIE_SAMESITE,
    )
    return response


def read_refresh_token(request) -> str | None:
    """Return the refresh token from the cookie, falling back to the body.

    The body fallback keeps non-browser clients (mobile, CLI, tests) working:
    they have no cookie jar, so they post the token explicitly.
    """
    cookie = request.COOKIES.get(settings.AUTH_COOKIE_NAME)
    if cookie:
        return cookie
    body = getattr(request, "data", None) or {}
    return body.get("refresh") or None
