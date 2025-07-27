from django.conf import settings
from django.utils import timezone
from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.accounts.email_service import send_verification_email_to_user

User = get_user_model()


def get_verification_url(obj):
    """Return the email verification URL for the user."""
    user = obj
    verification = user.email_verifications.filter(is_used=False, expires_at__gt=timezone.now()).first()
    if verification:
        return f"{settings.FRONTEND_URL}accounts/verify-email/{verification.token}/"
    return None

class UserSignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)
    verification_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'last_name', 'password', 'confirm_password',
            'phone', 'birth_date', 'gender', 'profile_image', 'age','verification_url'
        ]
        extra_kwargs = {
            'birth_date': {'write_only': True}
        }

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return data

    @staticmethod
    def get_verification_url(obj):
        return get_verification_url(obj)

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        user = User.objects.create_user(**validated_data)
        send_verification_email_to_user(user)
        return user


class VerifyEmailCodeSerializer(serializers.Serializer):
    verification_code = serializers.CharField(
        max_length=6,
        min_length=6,
        help_text="6-digit verification code"
    )


class ResendVerificationEmailSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True,write_only=True)
    verification_url = serializers.SerializerMethodField(read_only=True,)
    @staticmethod
    def get_verification_url(obj):
        return get_verification_url(obj)