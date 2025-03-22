from django.shortcuts import render

# Create your views here.
def help_center(request):
    return render(request, 'admin_panel/help_center.html')