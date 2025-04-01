from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.views.generic import TemplateView
from django.contrib.auth import logout
from admin_panel.decorators import admin_required
from django.views.decorators.cache import cache_control

@admin_required
def help_center(request):
    return render(request, 'admin_panel/help_center.html')
class LoginView(TemplateView):
    template_name = 'admin_panel/login.html'

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard')  # Redirect to home if user is already logged in
        return super().get(request, *args, **kwargs)

@cache_control(no_store=True, must_revalidate=True, no_cache=True)
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == "POST":
        email = request.POST.get('email')
        password = request.POST.get('password')

        # Manual validation
        if not email or not password:
            messages.error(request, 'Email and password are required.')
        elif "@" not in email or "." not in email:  # Basic email format validation
            messages.error(request, 'Invalid email format.')
        elif len(password) < 8: # Example password length validation
            messages.error(request, 'Password must be at least 8 characters long.')
        else:
            user = authenticate(username=email, password=password)  # Use email as username

            if user is not None:
                login(request, user)
                return redirect('dashboard' if user.is_superuser else 'dashboard')
            else:
                messages.error(request, 'Invalid email or password.')

    return render(request, 'admin_panel/login.html', {'form_type': 'login'})

@admin_required
def user_logout(request):
    logout(request)
    request.session.flush()  # Clear session data on logout
    return redirect('login')  