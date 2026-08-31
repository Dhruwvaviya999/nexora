"""Serializers for registration, the current user, profile updates and password reset."""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Public representation of a user (used for `me` and nested members)."""

    class Meta:
        model = User
        fields = (
            "id",
            "name",
            "email",
            "avatar",
            "is_active",
            "date_joined",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class RegisterSerializer(serializers.ModelSerializer):
    """Validates and creates a new user account."""

    password = serializers.CharField(
        write_only=True, style={"input_type": "password"}, validators=[validate_password]
    )
    password_confirm = serializers.CharField(
        write_only=True, style={"input_type": "password"}
    )

    class Meta:
        model = User
        fields = ("id", "name", "email", "password", "password_confirm")
        read_only_fields = ("id",)

    def validate_email(self, value: str) -> str:
        value = value.lower().strip()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")
        return User.objects.create_user(password=password, **validated_data)


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Fields a user is allowed to edit on their own profile."""

    class Meta:
        model = User
        fields = ("name", "avatar")


class LogoutSerializer(serializers.Serializer):
    """Refresh token to blacklist on logout."""

    refresh = serializers.CharField()


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Login serializer that returns the user object alongside the tokens.

    ``USERNAME_FIELD`` is already ``email``, so the parent handles credential
    validation — we only enrich the response.
    """

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data


class PasswordResetRequestSerializer(serializers.Serializer):
    """Email address to send a reset link to."""

    email = serializers.EmailField()

    def validate_email(self, value: str) -> str:
        return value.lower().strip()


class PasswordResetConfirmSerializer(serializers.Serializer):
    """A reset link's ``uid``/``token`` plus the new password.

    Validating the token here (rather than in the view) means an invalid link
    and a mismatched password are both reported the same way, as field errors.
    """

    uid = serializers.CharField()
    token = serializers.CharField()
    password = serializers.CharField(
        write_only=True, style={"input_type": "password"}, validators=[validate_password]
    )
    password_confirm = serializers.CharField(
        write_only=True, style={"input_type": "password"}
    )

    default_error_messages = {
        "invalid_link": "This password reset link is invalid or has expired.",
    }

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )

        try:
            user_id = force_str(urlsafe_base64_decode(attrs["uid"]))
            user = User.objects.get(pk=user_id)
        except (
            TypeError,
            ValueError,
            OverflowError,
            User.DoesNotExist,
            # The primary key is a UUID, so a malformed uid fails in the query
            # itself rather than simply matching nothing.
            DjangoValidationError,
        ):
            self.fail("invalid_link")

        if not default_token_generator.check_token(user, attrs["token"]):
            self.fail("invalid_link")

        attrs["user"] = user
        return attrs

    def save(self, **kwargs):
        user = self.validated_data["user"]
        user.set_password(self.validated_data["password"])
        user.save(update_fields=["password"])
        return user


def build_reset_credentials(user) -> tuple[str, str]:
    """Return the ``(uid, token)`` pair that identifies a reset link.

    The token is derived from the user's password hash and last-login time, so
    it stops working the moment the password changes or the link is used.
    """
    return urlsafe_base64_encode(force_bytes(user.pk)), default_token_generator.make_token(user)
