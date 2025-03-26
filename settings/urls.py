from django.urls import path
from . import views

urlpatterns = [
    path('settings/', views.settings, name='settings'),
    path("api/update-model-settings/", views.update_model_settings, name="update_model_settings"),
    path("api/update-aws-settings/", views.update_aws_settings, name="update_aws_settings"),
]