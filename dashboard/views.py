from django.shortcuts import render

# Create your views here.
def dashboard(request):
    return render(request, 'dashboard/dashboard.html')

def monitoring(request):
    return render(request, 'dashboard/monitoring.html')