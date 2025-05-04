from django.urls import path
from . import views

app_name = 'chatbot'

urlpatterns = [
    path('chatbot/qa/', views.qa_workflow, name='qa'),
    path('chatbot/history/', views.get_chat_history, name='history'),
    path('chatbot/feedback/', views.submit_feedback, name='feedback'),
]