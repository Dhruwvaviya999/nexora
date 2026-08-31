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
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

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
    """POST /auth/login/ — exchange email + password for JWT tokens."""

    serializer_class = EmailTokenObtainPairSerializer
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]


@extend_schema(tags=["auth"])
class LogoutView(APIView):
    """POST /auth/logout/ — blacklist the supplied refresh token."""

    permission_classes = [IsAuthenticated]
    serializer_class = LogoutSerializer

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            RefreshToken(serializer.validated_data["refresh"]).blacklist()
        except TokenError:
            return Response(
                {"detail": "Invalid or expired token."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_205_RESET_CONTENT)


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

        return Response(
            {"detail": "Password updated. You can sign in with your new password."},
            status=status.HTTP_200_OK,
        )


def _blacklist_all_refresh_tokens(user) -> None:
    """Revoke every outstanding refresh token belonging to ``user``."""
    for outstanding in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=outstanding)
