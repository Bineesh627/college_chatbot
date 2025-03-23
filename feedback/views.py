from django.shortcuts import render
from admin_panel.decorators import admin_required

@admin_required
def feedback(request):
    return render(request, 'feedback/feedback.html')