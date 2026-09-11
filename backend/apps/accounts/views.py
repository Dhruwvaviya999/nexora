"""Authentication and profile views."""

from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.timesince import timeuntil
from django.utils.timezone import now
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.accounts.cookies import (
    clear_refresh_cookie,
    read_refresh_token,
    set_refresh_cookie,
)
from apps.accounts.serializers import (
    EmailTokenObtainPairSerializer,
    LogoutSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    ProfileUpdateSerializer,
    RegisterSerializer,
    UserSerializer,
    build_reset_credentials,
)
from apps.common.email import frontend_url, queue_templated_email
from apps.common.throttling import (
    LoginRateThrottle,
    PasswordResetRateThrottle,
    RegisterRateThrottle,
)

User = get_user_model()


@extend_schema(tags=["auth"])
class RegisterView(generics.CreateAPIView):
    """POST /auth/register/ — create a new account."""

    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    throttle_classes = [RegisterRateThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["auth"])
class LoginView(TokenObtainPairView):
    """POST /auth/login/ — exchange email + password for JWT tokens.

    The access token is returned in the body (the client holds it in memory);
    the refresh token is moved out of the body into an **httpOnly** cookie so
    page script can never read the long-lived credential.
    """

    serializer_class = EmailTokenObtainPairSerializer
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            refresh = response.data.pop("refresh", None)
            if refresh:
                set_refresh_cookie(response, refresh)
        return response


@extend_schema(tags=["auth"])
class CookieTokenRefreshView(TokenRefreshView):
    """POST /auth/refresh/ — exchange the refresh cookie for a new access token.

    The token is read from the httpOnly cookie, so the request body is normally
    empty. Rotation is on, so a new refresh token comes back — it replaces the
    cookie and never reaches the body.
    """

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        token = read_refresh_token(request)
        if not token:
            return Response(
                {"detail": "No refresh token provided."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # SimpleJWT's serializer reads `refresh` from the request data; feed it
        # the cookie value so the caller does not have to know where it lives.
        serializer = self.get_serializer(data={"refresh": token})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as exc:  # pragma: no cover - defensive
            raise InvalidToken(exc.args[0]) from exc

        data = dict(serializer.validated_data)
        rotated = data.pop("refresh", None)

        response = Response(data, status=status.HTTP_200_OK)
        if rotated:
            set_refresh_cookie(response, rotated)
        return response


@extend_schema(tags=["auth"])
class LogoutView(APIView):
    """POST /auth/logout/ — blacklist the refresh token and clear the cookie.

    The token comes from the cookie; a body value is still accepted for
    non-browser clients. The cookie is cleared either way, so a client can
    always end its own session locally even if the token was already invalid.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = LogoutSerializer

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = read_refresh_token(request)
        if not token:
            return clear_refresh_cookie(
                Response(
                    {"detail": "No refresh token provided."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            )

        try:
            RefreshToken(token).blacklist()
        except TokenError:
            return clear_refresh_cookie(
                Response(
                    {"detail": "Invalid or expired token."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            )

        return clear_refresh_cookie(Response(status=status.HTTP_205_RESET_CONTENT))


@extend_schema(tags=["auth"])
class MeView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /auth/me/ — read or update the current user's profile."""

    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return ProfileUpdateSerializer
        return UserSerializer

    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        # Always return the full user representation after an update.
        return Response(UserSerializer(self.get_object()).data)


@extend_schema(tags=["auth"])
class PasswordResetRequestView(APIView):
    """POST /auth/password-reset/ — email a reset link.

    Always answers 202, whether or not the address belongs to an account.
    Saying "no such user" here would turn this endpoint into a way to test
    which email addresses are registered.
    """

    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetRateThrottle]
    serializer_class = PasswordResetRequestSerializer

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user is not None:
            uid, token = build_reset_credentials(user)
            queue_templated_email(
                template="password_reset",
                subject="Reset your Nexora password",
                to=user.email,
                context={
                    "name": user.name or user.email,
                    "email": user.email,
                    "reset_url": frontend_url(
                        f"/reset-password?uid={uid}&token={token}"
                    ),
                    "valid_for": timeuntil(
                        now() + timedelta(seconds=settings.PASSWORD_RESET_TIMEOUT), now()
                    ),
                },
            )

        return Response(
            {
                "detail": (
                    "If an account exists for that address, a reset link is on its way."
                )
            },
            status=status.HTTP_202_ACCEPTED,
        )


@extend_schema(tags=["auth"])
class PasswordResetConfirmView(APIView):
    """POST /auth/password-reset/confirm/ — set a new password from a reset link."""

    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetRateThrottle]
    serializer_class = PasswordResetConfirmSerializer

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Existing sessions were issued against the old credentials. Refresh
        # tokens outlive the reset by days, so anyone holding one (including
        # whoever prompted the reset) keeps access unless they are revoked.
        _blacklist_all_refresh_tokens(user)

        queue_templated_email(
            template="password_changed",
            subject="Your Nexora password was changed",
            to=user.email,
            context={
                "name": user.name or user.email,
                "email": user.email,
                "reset_url": frontend_url("/forgot-password"),
            },
        )

        # Every session was just revoked, including this browser's. Drop the
        # cookie too so the client is not left holding a token the server has
        # already blacklisted.
        return clear_refresh_cookie(
            Response(
                {"detail": "Password updated. You can sign in with your new password."},
                status=status.HTTP_200_OK,
            )
        )


def _blacklist_all_refresh_tokens(user) -> None:
    """Revoke every outstanding refresh token belonging to ``user``."""
    for outstanding in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=outstanding)
