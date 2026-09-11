"""
Authentication tests: password reset and the credential rate limits.

Password reset is the one flow that lets an unauthenticated caller change an
account's credentials, so the tests cover the abuse angles as much as the happy
path -- link reuse, tampering, account enumeration and session revocation.
"""

from __future__ import annotations

import re

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from rest_framework.test import APITestCase
from rest_framework.throttling import SimpleRateThrottle
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

from apps.accounts.serializers import build_reset_credentials

User = get_user_model()

RESET = "/api/v1/auth/password-reset/"
CONFIRM = "/api/v1/auth/password-reset/confirm/"
LOGIN = "/api/v1/auth/login/"

OLD = "0ld!Passw0rd"
NEW = "Br4nd!NewPassw0rd"


class PasswordResetTests(APITestCase):
    def setUp(self):
        # The request and confirm endpoints share one IP-keyed throttle bucket
        # that the cache carries across test methods. Rates are None under the
        # test settings, but clearing keeps these tests independent of each
        # other -- and of whichever settings module actually got loaded.
        cache.clear()
        self.addCleanup(cache.clear)

        self.user = User.objects.create_user(
            email="reset.me@example.com", password=OLD, name="Reset Me"
        )
        mail.outbox = []

    def request_reset(self, email):
        """Mail is queued in an on_commit hook, which TestCase must run explicitly."""
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(RESET, {"email": email}, format="json")

    def credentials(self):
        # The token hash covers last_login, which a login in the same test will
        # have moved on. Read the current row so the link is actually valid.
        self.user.refresh_from_db()
        return build_reset_credentials(self.user)

    # -- requesting ------------------------------------------------------
    def test_request_sends_a_link_to_a_known_address(self):
        response = self.request_reset(self.user.email)

        self.assertEqual(response.status_code, 202)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.user.email, mail.outbox[0].to)
        self.assertIn("/reset-password?uid=", mail.outbox[0].body)

    def test_the_emailed_link_is_not_html_escaped(self):
        """A text email must carry a literal "&", not "&amp;".

        Autoescaping would rename the second query parameter to "amp;token",
        so every emailed reset link would fail.
        """
        self.request_reset(self.user.email)

        body = mail.outbox[0].body
        self.assertNotIn("&amp;", body)
        self.assertRegex(body, r"/reset-password\?uid=[^&\s]+&token=\S+")

    def test_the_emailed_link_actually_works(self):
        """Pull the link out of the email and use it, exactly as a user would."""
        self.request_reset(self.user.email)

        match = re.search(r"/reset-password\?uid=([^&\s]+)&token=(\S+)", mail.outbox[0].body)
        self.assertIsNotNone(match, "no usable reset link in the email body")
        uid, token = match.groups()

        response = self.client.post(
            CONFIRM,
            {"uid": uid, "token": token, "password": NEW, "password_confirm": NEW},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW))

    def test_request_for_an_unknown_address_is_indistinguishable(self):
        """The response must not reveal whether an account exists."""
        known = self.request_reset(self.user.email)
        mail.outbox = []
        unknown = self.request_reset("nobody@example.com")

        self.assertEqual(unknown.status_code, known.status_code)
        self.assertEqual(unknown.data, known.data)
        self.assertEqual(len(mail.outbox), 0, "mailed a non-existent account")

    def test_request_is_case_insensitive(self):
        response = self.request_reset(self.user.email.upper())

        self.assertEqual(response.status_code, 202)
        self.assertEqual(len(mail.outbox), 1)

    def test_inactive_accounts_get_no_link(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        self.request_reset(self.user.email)

        self.assertEqual(len(mail.outbox), 0)

    def test_malformed_email_is_rejected(self):
        response = self.client.post(RESET, {"email": "not-an-email"}, format="json")
        self.assertEqual(response.status_code, 400)

    # -- confirming ------------------------------------------------------
    def test_valid_link_sets_the_new_password(self):
        uid, token = self.credentials()

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                CONFIRM,
                {"uid": uid, "token": token, "password": NEW, "password_confirm": NEW},
                format="json",
            )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW))
        self.assertFalse(self.user.check_password(OLD))

    def test_new_password_works_at_login_and_the_old_one_does_not(self):
        uid, token = self.credentials()
        self.client.post(
            CONFIRM,
            {"uid": uid, "token": token, "password": NEW, "password_confirm": NEW},
            format="json",
        )

        good = self.client.post(
            LOGIN, {"email": self.user.email, "password": NEW}, format="json"
        )
        bad = self.client.post(
            LOGIN, {"email": self.user.email, "password": OLD}, format="json"
        )

        self.assertEqual(good.status_code, 200)
        self.assertEqual(bad.status_code, 401)

    def test_a_link_cannot_be_used_twice(self):
        uid, token = self.credentials()
        payload = {"uid": uid, "token": token, "password": NEW, "password_confirm": NEW}

        first = self.client.post(CONFIRM, payload, format="json")
        second = self.client.post(CONFIRM, payload, format="json")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 400)

    def test_a_tampered_token_is_rejected(self):
        uid, token = self.credentials()

        response = self.client.post(
            CONFIRM,
            {
                "uid": uid,
                "token": token[:-1] + ("a" if token[-1] != "a" else "b"),
                "password": NEW,
                "password_confirm": NEW,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(OLD))

    def test_a_garbage_uid_is_rejected_not_a_server_error(self):
        """The primary key is a UUID, so a bad uid fails inside the query."""
        _, token = self.credentials()

        response = self.client.post(
            CONFIRM,
            {
                "uid": "!!!not-base64!!!",
                "token": token,
                "password": NEW,
                "password_confirm": NEW,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_another_users_uid_with_this_token_is_rejected(self):
        other = User.objects.create_user(
            email="other@example.com", password=OLD, name="Other"
        )
        _, token = self.credentials()
        other_uid, _ = build_reset_credentials(other)

        response = self.client.post(
            CONFIRM,
            {
                "uid": other_uid,
                "token": token,
                "password": NEW,
                "password_confirm": NEW,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        other.refresh_from_db()
        self.assertTrue(other.check_password(OLD))

    def test_mismatched_confirmation_is_rejected(self):
        uid, token = self.credentials()

        response = self.client.post(
            CONFIRM,
            {
                "uid": uid,
                "token": token,
                "password": NEW,
                "password_confirm": NEW + "x",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("password_confirm", response.data)

    def test_weak_passwords_are_rejected(self):
        uid, token = self.credentials()

        response = self.client.post(
            CONFIRM,
            {"uid": uid, "token": token, "password": "12345678", "password_confirm": "12345678"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.data)

    def test_reset_revokes_outstanding_refresh_tokens(self):
        """Whoever prompted the reset must not keep a working refresh token."""
        self.client.post(
            LOGIN, {"email": self.user.email, "password": OLD}, format="json"
        )
        # The refresh token is in an httpOnly cookie, not the response body.
        refresh = self.client.cookies[settings.AUTH_COOKIE_NAME].value
        self.assertTrue(refresh)

        uid, token = self.credentials()
        self.client.post(
            CONFIRM,
            {"uid": uid, "token": token, "password": NEW, "password_confirm": NEW},
            format="json",
        )

        self.assertTrue(BlacklistedToken.objects.filter(token__user=self.user).exists())
        # Explicit body, so the assertion holds even though the confirm
        # response also cleared the cookie.
        refreshed = self.client.post(
            "/api/v1/auth/refresh/", {"refresh": refresh}, format="json"
        )
        self.assertEqual(refreshed.status_code, 401)

    def test_confirmation_notifies_the_account_owner(self):
        uid, token = self.credentials()

        mail.outbox = []
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(
                CONFIRM,
                {"uid": uid, "token": token, "password": NEW, "password_confirm": NEW},
                format="json",
            )

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("changed", mail.outbox[0].subject.lower())


class CredentialThrottleTests(APITestCase):
    """The credential endpoints must refuse a burst of attempts."""

    # Deliberately tighter than production so a test needs only a few calls.
    RATES = {
        "login": "3/min",
        "register": "2/hour",
        "password_reset": "2/hour",
        "anon": None,
        "user": None,
        "ai": None,
    }

    def setUp(self):
        # DRF reads DEFAULT_THROTTLE_RATES into SimpleRateThrottle.THROTTLE_RATES
        # once, when the class is first imported, so override_settings cannot
        # reach it -- the class attribute has to be swapped directly.
        original = SimpleRateThrottle.THROTTLE_RATES
        SimpleRateThrottle.THROTTLE_RATES = self.RATES
        self.addCleanup(setattr, SimpleRateThrottle, "THROTTLE_RATES", original)

        # Throttle history lives in the cache; a bucket left over from another
        # test would make these results depend on execution order.
        cache.clear()
        self.addCleanup(cache.clear)

        self.user = User.objects.create_user(
            email="throttled@example.com", password=OLD, name="Throttled"
        )

    def test_repeated_failed_logins_are_throttled(self):
        payload = {"email": self.user.email, "password": "wrong-password"}

        statuses = [
            self.client.post(LOGIN, payload, format="json").status_code
            for _ in range(5)
        ]

        self.assertIn(429, statuses, f"login was never throttled: {statuses}")
        self.assertEqual(statuses[0], 401, "the first attempt should just fail")

    def test_bulk_registration_is_throttled(self):
        statuses = []
        for i in range(4):
            statuses.append(
                self.client.post(
                    "/api/v1/auth/register/",
                    {
                        "name": f"Bulk {i}",
                        "email": f"bulk{i}@example.com",
                        "password": NEW,
                        "password_confirm": NEW,
                    },
                    format="json",
                ).status_code
            )

        self.assertIn(429, statuses, f"registration was never throttled: {statuses}")

    def test_password_reset_requests_are_throttled(self):
        statuses = [
            self.client.post(RESET, {"email": self.user.email}, format="json").status_code
            for _ in range(4)
        ]

        self.assertIn(429, statuses, f"password reset was never throttled: {statuses}")


class RefreshCookieTests(APITestCase):
    """
    The refresh token must never reach JavaScript.

    It is issued as an httpOnly cookie, so an XSS can at worst steal the
    15-minute access token from memory — not a week-long session. These tests
    pin that contract end to end: issue, use, rotate, revoke.
    """

    PASSWORD = "S3cure!Passw0rd"

    def setUp(self):
        self.user = User.objects.create_user("cookie@example.com", self.PASSWORD)
        self.cookie_name = settings.AUTH_COOKIE_NAME

    def login(self):
        return self.client.post(
            LOGIN, {"email": self.user.email, "password": self.PASSWORD}, format="json"
        )

    # -- Issuing ------------------------------------------------------------

    def test_login_does_not_return_the_refresh_token_in_the_body(self):
        response = self.login()
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("user", response.data)
        self.assertNotIn("refresh", response.data)

    def test_login_sets_an_httponly_refresh_cookie(self):
        self.login()
        cookie = self.client.cookies[self.cookie_name]

        self.assertTrue(cookie.value)
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], settings.AUTH_COOKIE_SAMESITE)
        self.assertEqual(cookie["path"], settings.AUTH_COOKIE_PATH)

    def test_cookie_lifetime_matches_the_refresh_token_lifetime(self):
        self.login()
        expected = int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds())
        self.assertEqual(self.client.cookies[self.cookie_name]["max-age"], expected)

    # -- Using --------------------------------------------------------------

    def test_refresh_works_from_the_cookie_with_an_empty_body(self):
        self.login()
        response = self.client.post("/api/v1/auth/refresh/", {}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)

    def test_refresh_never_returns_the_rotated_token_in_the_body(self):
        """Rotation happens, but the replacement goes back into the cookie."""
        self.login()
        first = self.client.cookies[self.cookie_name].value

        response = self.client.post("/api/v1/auth/refresh/", {}, format="json")
        self.assertNotIn("refresh", response.data)

        rotated = self.client.cookies[self.cookie_name].value
        self.assertTrue(rotated)
        self.assertNotEqual(rotated, first)

    def test_rotated_token_makes_the_previous_one_unusable(self):
        self.login()
        original = self.client.cookies[self.cookie_name].value
        self.client.post("/api/v1/auth/refresh/", {}, format="json")

        # Drop the (valid, rotated) cookie first: `read_refresh_token` prefers
        # the cookie over the body, so leaving it in place would just refresh
        # successfully and prove nothing about the old token.
        del self.client.cookies[self.cookie_name]

        replayed = self.client.post(
            "/api/v1/auth/refresh/", {"refresh": original}, format="json"
        )
        self.assertEqual(replayed.status_code, 401)

    def test_refresh_without_a_cookie_or_body_is_unauthorized(self):
        response = self.client.post("/api/v1/auth/refresh/", {}, format="json")
        self.assertEqual(response.status_code, 401)

    def test_the_access_token_actually_authenticates(self):
        access = self.login().data["access"]
        response = self.client.get(
            "/api/v1/auth/me/", HTTP_AUTHORIZATION=f"Bearer {access}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], self.user.email)

    def test_body_fallback_still_works_for_non_browser_clients(self):
        """Mobile and CLI clients have no cookie jar, so they post the token."""
        self.login()
        token = self.client.cookies[self.cookie_name].value
        del self.client.cookies[self.cookie_name]

        response = self.client.post(
            "/api/v1/auth/refresh/", {"refresh": token}, format="json"
        )
        self.assertEqual(response.status_code, 200)

    # -- Revoking -----------------------------------------------------------

    def test_logout_blacklists_the_cookie_token_and_clears_it(self):
        access = self.login().data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        response = self.client.post("/api/v1/auth/logout/", {}, format="json")
        self.assertEqual(response.status_code, 205)

        self.assertTrue(BlacklistedToken.objects.filter(token__user=self.user).exists())
        # An empty value on the response is how a cookie is deleted.
        self.assertEqual(self.client.cookies[self.cookie_name].value, "")

    def test_refresh_after_logout_is_rejected(self):
        access = self.login().data["access"]
        token = self.client.cookies[self.cookie_name].value
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        self.client.post("/api/v1/auth/logout/", {}, format="json")

        response = self.client.post(
            "/api/v1/auth/refresh/", {"refresh": token}, format="json"
        )
        self.assertEqual(response.status_code, 401)

    def test_password_reset_confirm_clears_the_cookie(self):
        self.login()
        # The reset token hash covers last_login, which the login above just
        # moved on. Re-read the row or the link is built from stale state and
        # is rejected as invalid.
        self.user.refresh_from_db()
        uid, token = build_reset_credentials(self.user)

        response = self.client.post(
            CONFIRM,
            {"uid": uid, "token": token, "password": NEW, "password_confirm": NEW},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.cookies[self.cookie_name].value, "")
