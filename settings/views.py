from django.shortcuts import render, redirect
from admin_panel.decorators import admin_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import check_password
from django.contrib.auth import update_session_auth_hash
from django.http import JsonResponse
from model_api.models import ModelSettings
from django.views.decorators.csrf import csrf_protect
import re
# from django.contrib.auth.decorators import login_required

@admin_required
# @login_required
def settings(request):
    settings = ModelSettings.objects.first()
    user = request.user

    if request.method == 'POST':
        if 'email_update' in request.POST:
            fname = request.POST.get('first_name', '').strip()
            lname = request.POST.get('last_name', '').strip()
            email = request.POST.get('email', '').strip()

            # Name validation
            name_pattern = re.compile(r"^[A-Za-z-' ]+$")
            if not fname or not lname:
                messages.error(request, 'First name and last name cannot be empty.')
            elif not name_pattern.match(fname) or not name_pattern.match(lname):
                messages.error(request, 'Names must contain only alphabets, spaces, hyphens, or apostrophes.')
            else:
                # Validate email
                try:
                    validate_email(email)
                except ValidationError:
                    messages.error(request, 'Invalid email format.')
                else:
                    # Update first name and last name if changed
                    if fname != user.first_name or lname != user.last_name:
                        user.first_name = fname
                        user.last_name = lname
                        user.save()
                        messages.success(request, 'Name updated successfully.')
                    else:
                        messages.info(request, 'No changes detected in name fields.')

                    # Update email if changed
                    if email and email != user.email:
                        user.email = email
                        user.save()
                        messages.success(request, 'Email updated successfully.')
                    else:
                        messages.info(request, 'No changes detected in email field.')
        elif 'password_change' in request.POST:
            old_password = request.POST.get('current_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')

            # Validate old password
            if not check_password(old_password, user.password):
                messages.error(request, "Old password is incorrect.")
            else:
                # Validate new password
                if new_password != confirm_password:
                    messages.error(request, "New password and confirm password do not match.")
                elif len(new_password) < 8:
                    messages.error(request, "New password must be at least 8 characters long.")
                else:
                    # Set the new password
                    user.set_password(new_password)
                    user.save()

                    # Update session to prevent logout after password change
                    update_session_auth_hash(request, user)

                    messages.success(request, "Your password was successfully updated!")

    return render(request, 'settings/settings.html', {'user': user, 'settings': settings})

@csrf_protect
def update_model_settings(request):
    """Update LLaMA Model Settings"""
    if request.method == "POST":
        try:
            settings, _ = ModelSettings.objects.get_or_create(model_id=1)
            settings.model_version = request.POST.get("model_version")
            settings.temperature = float(request.POST.get("temperature"))
            settings.max_tokens = int(request.POST.get("max_tokens"))
            settings.context_window = int(request.POST.get("context_window"))
            settings.save()
            return JsonResponse({"success": True, "message": "Model settings updated!"})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)
    
    return JsonResponse({"success": False, "error": "Invalid request method"}, status=405)

@csrf_protect
def update_aws_settings(request):
    """Update AWS Bedrock Settings"""
    if request.method == "POST":
        try:
            settings, _ = ModelSettings.objects.get_or_create(model_id=1)
            settings.aws_region = request.POST.get("aws_region")
            settings.api_key = request.POST.get("api_key")
            settings.secret_key = request.POST.get("secret_key")
            settings.save()
            return JsonResponse({"success": True, "message": "AWS settings updated!"})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)
    
    return JsonResponse({"success": False, "error": "Invalid request method"}, status=405)
