from django.shortcuts import render
from django.views.decorators.cache import cache_control

@cache_control(no_store=True, must_revalidate=True, no_cache=True)
def home(request):
    return render(request, 'college_interface/home.html')