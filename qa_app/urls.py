# qa_app/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.qa_workflow, name='qa_workflow'), # Main workflow view
    # ... other URLs for different components later ...
]