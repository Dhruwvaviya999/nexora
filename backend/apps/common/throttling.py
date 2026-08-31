"""
Named throttle scopes.

Rates are configured in settings under REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
so they can be tuned per environment without touching code.

Credential endpoints are throttled by IP rather than by user: the whole point
is to limit an attacker who has no valid account yet, and who would otherwise
get a fresh bucket for every email address they guess.
"""

from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    """Limits credential-stuffing against /auth/login/."""

    scope = "login"


class RegisterRateThrottle(AnonRateThrottle):
    """Limits bulk account creation."""

    scope = "register"


class PasswordResetRateThrottle(SimpleRateThrottle):
    """Limits /auth/password-reset/, which also sends mail.

    Keyed by IP for anonymous callers -- rate limiting by the submitted email
    address would let an attacker lock a specific person out of resets.
    """

    scope = "password_reset"

    def get_cache_key(self, request, view):
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class AIRateThrottle(SimpleRateThrottle):
    """Limits LLM-backed endpoints, which cost money per call."""

    scope = "ai"

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}
