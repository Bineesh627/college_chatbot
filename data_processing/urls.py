from django.urls import path
from . import views

# app_name = 'data_processing'  # <--- ENSURE THIS LINE IS PRESENT AND CORRECT

urlpatterns = [
    path('data_source/', views.data_source, name='data_source'),
    path('embedding_process/', views.start_embedding, name='embedding_process'),
    path('content_process/', views.start_content, name='content_process'),
    path('pdf_process/', views.pdf_process, name='pdf_process'),
]