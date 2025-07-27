from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from apps.accounts.email_service import send_verification_email_to_user
from apps.accounts.models.verification_codes import EmailVerificationCode
from django.contrib.auth import get_user_model
from apps.accounts.serializers import (
    UserSignupSerializer, VerifyEmailCodeSerializer, ResendVerificationEmailSerializer,
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView, TokenBlacklistView, TokenRefreshView, TokenVerifyView,
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
            response.data['message'] = 'Login successful.'
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

class VerifyEmailCodeView(generics.UpdateAPIView):
    serializer_class = VerifyEmailCodeSerializer
    queryset = EmailVerificationCode.objects.all()
    permission_classes = [AllowAny]
    lookup_field = 'token'

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            verification_code = serializer.validated_data['verification_code']

            try:
                verification = EmailVerificationCode.objects.get(
                    verification_code=verification_code,
                    is_used=False,
                )
                if verification.is_expired():
                    return Response({
                        "success": False,
                        "detail": "Verification code has expired."
                    }, status=status.HTTP_400_BAD_REQUEST)

                if verification.user.is_active:
                    return Response({
                        "success": False,
                        "detail": "Email is already verified."
                    }, status=status.HTTP_400_BAD_REQUEST)

                verification.user.is_active = True
                verification.user.save()

                verification.is_used = True
                verification.save()

                return Response({
                    "success": True,
                    "detail": "Email successfully verified."
                }, status=status.HTTP_200_OK)

            except EmailVerificationCode.DoesNotExist:
                return Response({
                    "success": False,
                    "detail": "Invalid verification code."
                }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "success": False,
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class ResendVerificationEmailView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = ResendVerificationEmailSerializer

    def post(self, request):
        """Resend verification email to the user"""
        user = User.objects.get(email=request.data['email'])

        # Check if user is already verified
        if user.is_active:
            return Response(
                {
                    'success': False,
                    'message': 'Email is already verified'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            send_verification_email_to_user(user)
            return Response(
                {
                    'success': True,
                    'message': 'Verification email sent successfully',
                    'verification_url': self.get_serializer_class().get_verification_url(user)
                },
                status=status.HTTP_200_OK
            )
        except Exception:
            return Response(
                {
                    'success': False,
                    'message': 'Failed to send verification email'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )