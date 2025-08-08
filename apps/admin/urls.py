from django.urls import path
from apps.admin.views import home, admin_profile,CustomLogoutView
from django.contrib.auth.views import LoginView

urlpatterns = [
    path('', home, name='home'),
    path('profile/', admin_profile, name='admin_profile'),
    path('login/', LoginView.as_view(
        template_name='admin/login.html',
    ), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
]