from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.accounts.views import (
    SignupView, LoginView, LogoutView, RefreshTokenView, VerifyTokenView, VerifyEmailCodeView,
    ResendVerificationEmailView, GoogleAuthenticationView, UserTypeUpdateView, ProfileViewSet,
    GetProfilesViewSet,DeleteUser
)

app_name= 'accounts'

router = DefaultRouter()
router.register(r'profile', ProfileViewSet, basename='profile')
router.register(r'profiles', GetProfilesViewSet, basename='profiles')
urlpatterns = [
    path('signup/', SignupView.as_view(), name='user-signup'),
    path('login/', LoginView.as_view(), name='user-login'),
    path('refresh/', RefreshTokenView.as_view(), name='user-refresh'),
    path('verify/', VerifyTokenView.as_view(), name='user-verify'),
    path('logout/', LogoutView.as_view(), name='user-logout'),
    path('delete/', DeleteUser.as_view(), name='user-delete'),
    path('verify-email/<token>/', VerifyEmailCodeView.as_view(), name='verify-verification-code'),
    path('resend-verification-email/', ResendVerificationEmailView.as_view(), name='resend-verification-email'),
    path('google/auth/', GoogleAuthenticationView.as_view(), name='google-auth'),
    path('type/update/', UserTypeUpdateView.as_view(), name='user-type-update'),
    path('', include(router.urls)),
]
