from django.urls import path
from apps.accounts.views import (
    SignupView, LoginView, LogoutView, RefreshTokenView, VerifyTokenView, VerifyEmailCodeView,
    ResendVerificationEmailView
)
app_name= 'accounts'

urlpatterns = [
    path('signup/', SignupView.as_view(), name='user-signup'),
    path('login/', LoginView.as_view(), name='user-login'),
    path('refresh/', RefreshTokenView.as_view(), name='user-refresh'),
    path('verify/', VerifyTokenView.as_view(), name='user-verify'),
    path('logout/', LogoutView.as_view(), name='user-logout'),
    path('verify-email/<token>/', VerifyEmailCodeView.as_view(), name='verify-verification-code'),
    path('resend-verification-email/', ResendVerificationEmailView.as_view(), name='resend-verification-email'),
    # path('google/auth/', GoogleAuthView.as_view(), name='google-signup'),
]
