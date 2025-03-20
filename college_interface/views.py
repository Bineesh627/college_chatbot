from django.shortcuts import render

def home(request):
    return render(request, 'college_interface/home.html')