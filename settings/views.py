from django.shortcuts import render
from admin_panel.decorators import admin_required

@admin_required
def settings(request):
    return render(request, 'settings/settings.html')