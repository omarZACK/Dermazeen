from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, reverse
from django.http import HttpResponseForbidden
from django.views import View
from django.contrib import messages
from apps.admin.forms import AdminProfileForm
from apps.admin.models import Admin

def admin_only(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # 1) Make sure the user is logged in
        if not request.user.is_authenticated:
            # You could also use the login_required decorator separately,
            # or redirect to your login page here:
            return redirect('admin:login')

        # 2) Try to fetch the Admin instance; if none exists, block access
        try:
            _ = request.user.admin
        except Admin.DoesNotExist:
            return HttpResponseForbidden("Access Denied: Admins only.")

        # 3) If we got here, the user has an Admin record—allow the view
        return view_func(request, *args, **kwargs)

    return _wrapped_view


@admin_only
@login_required
def home(request):
    """
    Redirects authenticated users to the admin site.
    """
    return redirect(reverse('admin:index'))

@admin_only
@login_required
def admin_profile(request):
    user = request.user
    if request.method == 'POST':
        form = AdminProfileForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            return redirect('admin_profile')
    else:
        form = AdminProfileForm(instance=user)

    return render(request, 'admin/admin_profile.html', {
        'form': form,
        'user': user,
        'admin': getattr(user, 'admin', None)
    })

class CustomLogoutView(View):
    def get(self, request):
        if request.user.is_authenticated:
            logout(request)
            messages.success(request, "You have been successfully logged out.")
            return redirect(reverse('logout') + '?logout=true')
        else:
            messages.info(request, "You were already logged out.")
            return render(request, 'admin/registration/logged_out.html')