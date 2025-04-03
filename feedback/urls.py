from django.urls import path
from . import views

urlpatterns = [
    path('feedback/', views.feedback, name='feedback'),
    path('api/get-response-accuracy/', views.get_response_accuracy, name='get_response_accuracy'),
    path('api/get-common-topics/', views.get_common_topics, name='get_common_topics'),
    path('api/get-quality-trends/', views.get_quality_trends, name='get_quality_trends'),
    path('api/get-total-responses/', views.get_total_responses, name='get_total_responses'),
]