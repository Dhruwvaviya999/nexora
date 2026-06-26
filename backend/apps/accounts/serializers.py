"""Serializers for registration, the current user, and profile updates."""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
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
