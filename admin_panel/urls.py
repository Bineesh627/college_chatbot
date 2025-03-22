from django.urls import path
from . import views

urlpatterns = [
    path('help/', views.help_center, name='help'),
]