from django.urls import path
from . import views

urlpatterns = [
    path('pdf_process/', views.pdf_process, name='pdf_process'),
]