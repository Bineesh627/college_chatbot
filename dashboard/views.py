from django.shortcuts import render
from admin_panel.decorators import admin_required

@admin_required
def dashboard(request):
    return render(request, 'dashboard/dashboard.html')

@admin_required
def monitoring(request):
    return render(request, 'dashboard/monitoring.html')