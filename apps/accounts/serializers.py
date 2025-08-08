from django.conf import settings
from django.utils import timezone
from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.accounts.email_service import send_verification_email_to_user
from apps.accounts.models import PatientProfile, Doctor
from django.utils.translation import gettext_lazy as _
from apps.shared.enums import GenderChoices, UserTypeChoices, SkinTypeChoices, ApprovalStatusChoices

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
    user_type = serializers.CharField(read_only=True)
    verification_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'password',
            'confirm_password','phone', 'birth_date', 'gender',
            'age', 'verification_url', 'profile_image','user_type'
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
    email = serializers.EmailField(required=True, write_only=True)
    verification_url = serializers.SerializerMethodField(read_only=True, )

    @staticmethod
    def get_verification_url(obj):
        return get_verification_url(obj)

class GoogleSerializer(serializers.ModelSerializer):
    """Serializer for Google token authentication"""
    token = serializers.CharField(required=True)
    gender = serializers.ChoiceField(choices=GenderChoices.choices, required=False)
    birth_date = serializers.DateField(required=False)
    phone = serializers.CharField(required=False)

    class Meta:
        model = User
        fields = [
            'token', 'gender', 'birth_date', 'phone',
        ]

class UserTypeSelectionSerializer(serializers.ModelSerializer):
    """Serializer for selecting user type"""
    user_type = serializers.ChoiceField(
        error_messages={
            'invalid_choice': _('Please select either "patient" or "doctor" as your user type.'),
        },
        choices=UserTypeChoices.choices[0:2],
        required=True)

    class Meta:
        model = User
        fields = ['user_type']

class UserProfile(serializers.ModelSerializer):
    full_name = serializers.CharField(source='get_full_name')
    class Meta:
        model = User
        fields = [
            'id','email','full_name', 'birth_date', 'gender', 'phone', 'user_type', 'profile_image'
        ]
        read_only_fields = [
            'id','email','full_name', 'birth_date', 'gender', 'phone', 'user_type', 'profile_image'
        ]

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['user_type'] = instance.get_user_type_display()
        representation['gender'] = instance.get_gender_display()
        representation['profile_image'] = f'{settings.FRONTEND_URL}{instance.profile_image}'
        return representation

class BaseProfileSerializer(serializers.Serializer):
    """Base serializer with common user fields"""
    id = serializers.IntegerField(source='user.id', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    first_name = serializers.CharField(source='user.first_name', write_only=True)
    last_name = serializers.CharField(source='user.last_name', write_only=True)
    birth_date = serializers.DateField(source='user.birth_date', required=False)
    gender = serializers.CharField(source='user.get_gender_display', required=False)
    phone = serializers.CharField(source='user.phone', required=False)
    user_type = serializers.CharField(source='user.get_user_type_display', read_only=True)
    profile_image = serializers.ImageField(source='user.profile_image', required=False)

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        if user_data:
            user = instance.user
            for attr, value in user_data.items():
                setattr(user, attr, value)
            user.save()
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

class PatientProfileSerializer(BaseProfileSerializer, serializers.ModelSerializer):
    """Serializer for patient profile setup"""
    skin_type = serializers.ChoiceField(choices=SkinTypeChoices.choices, required=False)
    is_pregnant = serializers.BooleanField(default=False)
    lifestyle_factors = serializers.JSONField(default=dict, required=False)

    # Add computed fields
    completion_percentage = serializers.IntegerField(read_only=True)
    profile_completed = serializers.BooleanField(read_only=True)

    class Meta:
        model = PatientProfile
        fields = [
            'id','email','full_name', 'first_name', 'last_name',
            'birth_date','gender', 'phone', 'user_type',
            'profile_image', 'skin_type', 'is_pregnant',
            'lifestyle_factors', 'completion_percentage', 'profile_completed'
        ]

    def update(self, instance, validated_data):
        """Override update method to handle patient-specific updates"""
        super().update(instance, validated_data)
        instance.calculate_completion_percentage()
        instance.save()
        return instance

class DoctorProfileSerializer(BaseProfileSerializer, serializers.ModelSerializer):
    """Serializer for doctor profile setup"""
    license_number = serializers.CharField(max_length=50)
    specialization = serializers.CharField(max_length=100)
    qualifications = serializers.CharField()
    is_available = serializers.BooleanField(default=True)
    approval_status = serializers.ChoiceField(choices=ApprovalStatusChoices.choices,read_only=True)

    class Meta:
        model = Doctor
        fields = [
            'id','email','full_name', 'first_name', 'last_name',
            'birth_date','gender', 'phone', 'user_type',
            'profile_image', 'license_number', 'specialization',
            'qualifications','is_available','approval_status'
        ]