from django.urls import path
from . import views

urlpatterns = [
    path('pdf_process/', views.manage_uploaded_pdfs, name='pdf_process'),
]