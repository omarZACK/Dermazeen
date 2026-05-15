from django.db import transaction
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import update_last_login
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ReadOnlyModelViewSet
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenBlacklistView, TokenRefreshView, TokenVerifyView
from apps.accounts.authentication import GoogleAuthentication
from apps.accounts.email_service import send_verification_email_to_user
from apps.accounts.models import EmailVerificationCode, PatientProfile, Doctor
from apps.shared.enums import UserTypeChoices, ApprovalStatusChoices
from apps.shared.permissions import IsAuthenticatedUser
from apps.shared.utils import download_image
from apps.accounts.serializers import (
    UserSignupSerializer, VerifyEmailCodeSerializer, ResendVerificationEmailSerializer,
    GoogleSerializer, UserProfile, UserTypeSelectionSerializer, PatientProfileSerializer,
    DoctorProfileSerializer,
)

User = get_user_model()

class SignupView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSignupSerializer
    permission_classes = [AllowAny]

class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            user = User.objects.get(email=request.data['email'])
            response.data['user'] = UserProfile(user).data
            response.data['message'] = _('Login successful.')
        return response

class LogoutView(TokenBlacklistView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            response.data['message'] = 'Logged out successfully.'
        return response

class RefreshTokenView(TokenRefreshView):
    permission_classes = [AllowAny]
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            response.data['message'] = 'Refresh token successfully.'
        return response

class VerifyTokenView(TokenVerifyView):
    permission_classes = [AllowAny]
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            response.data['message']  = 'Verify token successfully.'
        return response

class DeleteUser(generics.DestroyAPIView):
    permission_classes = [IsAuthenticatedUser]
    queryset = User.objects.all()

    def get_object(self):
        return self.request.user

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        self.perform_destroy(user)
        return Response({'message': _("User deleted successfully.")}, status=status.HTTP_204_NO_CONTENT)

class VerifyEmailCodeView(generics.UpdateAPIView):
    serializer_class = VerifyEmailCodeSerializer
    queryset = EmailVerificationCode.objects.all()
    permission_classes = [AllowAny]
    lookup_field = 'token'

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            verification_code = serializer.validated_data['verification_code']

            # Use filter to find the verification code instead of try-except
            verification = EmailVerificationCode.objects.filter(
                verification_code=verification_code,
                is_used=False,
            ).first()

            if not verification:
                return Response({
                    "success": False,
                    "detail": _("Invalid verification code.")
                }, status=status.HTTP_400_BAD_REQUEST)

            if verification.is_expired():
                return Response({
                    "success": False,
                    "detail": _("Verification code has expired.")
                }, status=status.HTTP_400_BAD_REQUEST)

            if verification.user.is_active:
                return Response({
                    "success": False,
                    "detail": _("Email is already verified.")
                }, status=status.HTTP_400_BAD_REQUEST)

            # Mark the user as active and the verification code as used
            verification.user.is_active = True
            verification.user.save()

            verification.is_used = True
            verification.save()

            return Response({
                "success": True,
                "detail": _("Email successfully verified.")
            }, status=status.HTTP_200_OK)

        return Response({
            "success": False,
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class ResendVerificationEmailView(generics.GenericAPIView):
    serializer_class = ResendVerificationEmailSerializer

    def post(self, request):
        """Resend verification email to the user"""
        user = User.objects.filter(email=request.data['email']).first()

        if not user:
            return Response(
                {
                    'success': False,
                    'message': _('User not found')
                },
                status=status.HTTP_404_NOT_FOUND
            )

        if user.is_active:
            return Response(
                {
                    'success': False,
                    'message': _('Email is already verified')
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        verification_url = self.get_serializer_class().get_verification_url(user)
        send_status = send_verification_email_to_user(user)

        if send_status:
            return Response(
                {
                    'success': True,
                    'message': _('Verification email sent successfully'),
                    'verification_url': verification_url
                },
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {
                    'success': False,
                    'message': _('Failed to send verification email')
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class GoogleAuthenticationView(generics.GenericAPIView):
    serializer_class = GoogleSerializer
    queryset = User.objects.all()
    authentication_classes = [GoogleAuthentication]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Invalid data", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        validated_data = serializer.validated_data
        gender = validated_data.get('gender')
        birth_date = validated_data.get('birth_date')

        # Get Google user data
        google_user_data = self._get_google_user_data(validated_data['token'])

        if not google_user_data:
            return Response(
                {"error": "Authentication failed",
                 "message": "Invalid Google token"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Extract user information from Google data
        email = google_user_data.get('email')
        first_name = google_user_data.get('given_name')
        last_name = google_user_data.get('family_name')
        picture_url = google_user_data.get('picture')
        is_active = google_user_data.get('verified_email', False)

        if not email:
            return Response(
                {"error": "Authentication failed",
                 "message": "Email not found in Google profile"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if user already exists
        existing_user = self.get_queryset().filter(email=email).first()

        if existing_user:
            # User exists, update their tokens and return
            tokens = self._generate_tokens(existing_user)
            return Response({
                "success": True,
                "message": "Authentication successful",
                "user": UserProfile(existing_user).data,
                "tokens": tokens
            }, status=status.HTTP_200_OK)
        else:

            missing_fields = []
            if not gender or gender == '':
                missing_fields.append('gender')
            if not birth_date:
                missing_fields.append('birth_date')

            if missing_fields:
                return Response({
                    "error": "Required fields missing for new account creation",
                    "message": f"Please provide the following required fields: {', '.join(missing_fields)}",
                    "missing_fields": missing_fields
                }, status=status.HTTP_400_BAD_REQUEST)

            user_data = {
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'is_active': is_active,
                'gender': gender,
                'birth_date': birth_date
            }

            if picture_url:
                image_data = self._download_google_profile_image(picture_url)
                if image_data:
                    user_data['profile_image'] = image_data
            user = self.get_queryset().create(**user_data)
            if user:
                tokens = self._generate_tokens(user)
                return Response({
                    "success": True,
                    "message": "New account created successfully",
                    "user": UserProfile(user).data,
                    "tokens": tokens
                }, status=status.HTTP_201_CREATED)
            else:
                return Response(
                    {"error": "User creation failed", "message": "Could not create user account"},
                    status=status.HTTP_400_BAD_REQUEST
                )

    @staticmethod
    def _get_google_user_data(token: str):
        auth = GoogleAuthentication()
        return auth.get_google_info(token)

    @staticmethod
    def _generate_tokens(user):
        refresh = RefreshToken.for_user(user)
        update_last_login(user=user,sender=None)
        return {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }

    def _download_google_profile_image(self, image_url):
        return download_image(self.queryset, image_url)

class UserTypeUpdateView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticatedUser]
    serializer_class = UserTypeSelectionSerializer
    http_method_names = ['patch']

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response({
            'message': _('type selected successfully.'),
            'user_type': _(instance.user_type)
        },status=status.HTTP_200_OK)

class ProfileViewSet(GenericViewSet):
    permission_classes = [IsAuthenticatedUser]

    def get_serializer_class(self):
        return {
            UserTypeChoices.PATIENT: PatientProfileSerializer,
            UserTypeChoices.DOCTOR: DoctorProfileSerializer,
        }.get(self.request.user.user_type)

    def get_object(self):
        user = self.request.user
        if user.user_type == UserTypeChoices.PATIENT:
            profile, created = PatientProfile.objects.get_or_create(user=user)
            return profile
        elif user.user_type == UserTypeChoices.DOCTOR:
            profile, created = Doctor.objects.get_or_create(user=user)
            return profile
        else:
            return user

    @action(detail=False, methods=['get'], url_path='current')
    def get_current_profile(self, request):
        if not request.user.user_type:
            return Response(
                {'error': _('User type not set. Please select user type first.')},
                status=status.HTTP_400_BAD_REQUEST
            )
        profile = self.get_object()
        serializer = self.get_serializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post', 'patch'], url_path='setup')
    def setup_profile(self, request):
        user = request.user
        if not user.user_type:
            return Response(
                {'error': _('User type not set. Please select user type first.')},
                status=status.HTTP_400_BAD_REQUEST
            )

        if user.user_type not in [UserTypeChoices.PATIENT, UserTypeChoices.DOCTOR]:
            return Response(
                {'error': _('Invalid user type for profile setup.')},
                status=status.HTTP_400_BAD_REQUEST
            )
        profile = self.get_object()
        serializer = self.get_serializer(profile, data=request.data, partial=True)

        if serializer.is_valid():
            with transaction.atomic():
                updated_profile = serializer.save()
                response_data = {
                    'message': _(f'{user.get_user_type_display()} profile updated successfully.'),
                    'profile': serializer.data
                }
                if user.user_type == UserTypeChoices.DOCTOR:
                    response_data['requires_approval'] = updated_profile.approval_status == (
                            'pending' or 'suspended' or 'rejected')

                return Response(response_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='doctor-approval-status')
    def get_doctor_approval_status(self, request):
        user = request.user

        if user.user_type != UserTypeChoices.DOCTOR:
            return Response(
                {'error': _('This endpoint is only available for doctors.')},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not hasattr(user, 'doctor'):
            return Response(
                {'error': _('Doctor profile not found.')},
                status=status.HTTP_404_NOT_FOUND
            )

        doctor = user.doctor

        return Response(
            {
                'approval_status': doctor.get_approval_status_display(),
                'approved_at': doctor.approved_at,
                'approved_by': doctor.approved_by.user.get_full_name() if doctor.approved_by else None,
                'rejection_reason': doctor.rejection_reason,
                'is_available': doctor.is_available,
                'consultation_count': doctor.consultation_count,
                'rating': doctor.rating
            },
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['post'], url_path='lifestyle/setup')
    def add_lifestyle_factor(self, request):
        key = request.data.get('key')
        value = request.data.get('value')

        if not key or not value:
            return Response({'error': _('Both Key and Value is required.')}, status=status.HTTP_400_BAD_REQUEST)

        profile = self.get_object()
        profile.lifestyle_factors = profile.lifestyle_factors or {}
        profile.lifestyle_factors[key] = value
        profile.save()

        return Response(
            {'message': _('Lifestyle factor added/updated.'), 'lifestyle_factors': profile.lifestyle_factors}
        )

    @action(detail=False, methods=['delete'], url_path='lifestyle/delete')
    def delete_lifestyle_factor(self, request):
        key = request.query_params.get('key')
        if not key:
            return Response({'error': _('Key is required.')}, status=status.HTTP_400_BAD_REQUEST)

        profile = self.get_object()
        if not profile.lifestyle_factors or key not in profile.lifestyle_factors:
            return Response({'error': _('Key not found.')}, status=status.HTTP_404_NOT_FOUND)

        profile.lifestyle_factors.pop(key)
        profile.save()

        return Response({'message': _('Lifestyle factor deleted.'), 'lifestyle_factors': profile.lifestyle_factors})

class GetProfilesViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]

    def _get_type(self):
        t = self.request.query_params.get('type')
        if t not in (UserTypeChoices.DOCTOR, UserTypeChoices.PATIENT):
            raise ValidationError({
                'type': "Query-param `type` is required and must be 'doctor' or 'patient'."
            })
        return t

    def get_queryset(self):
        t = self._get_type()
        return {
            UserTypeChoices.DOCTOR: Doctor.objects.filter(approval_status=ApprovalStatusChoices.APPROVED),
            UserTypeChoices.PATIENT: PatientProfile.objects.all(),
        }[t]

    def get_serializer_class(self):
        t = self._get_type()
        return {
            UserTypeChoices.DOCTOR: DoctorProfileSerializer,
            UserTypeChoices.PATIENT: PatientProfileSerializer,
        }[t]