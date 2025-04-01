from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('monitoring/', views.monitoring, name='monitoring'),
    path('api/analytics/', views.analytics_api, name='analytics_api'),
]