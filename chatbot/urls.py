from django.urls import path
from . import views

urlpatterns = [
    path('qa_workflow/', views.qa_workflow, name='qa_workflow'), # Main workflow view
    path('get_chat_history/', views.get_chat_history, name='get_chat_history'),
]