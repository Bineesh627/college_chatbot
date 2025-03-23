from django.urls import path
from . import views

urlpatterns = [
    path('help/', views.help_center, name='help'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.user_logout, name='logout'),
]