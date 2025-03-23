from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

def admin_required(view_func):
    """
    Decorator to allow only admin users to access a view.
    Redirects non-authenticated users to login.
    Raises a PermissionDenied error for non-admin users.
    """
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')  # Redirect unauthenticated users to login

        if not request.user.is_staff:  # Only staff (admin) can access
            raise PermissionDenied  # Return 403 Forbidden error for non-admins

        return view_func(request, *args, **kwargs)

    return _wrapped_view
