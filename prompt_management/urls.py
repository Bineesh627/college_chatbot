from django.urls import path
from . import views

urlpatterns = [
    path('api/prompt/', views.view_prompt, name='view_prompt'),
    path('api/prompts/', views.get_prompts, name='get_prompts'),
    path('api/prompts/add/', views.add_prompt, name='add_prompt'),
    path('api/prompts/edit/<int:prompt_id>/', views.edit_prompt, name='edit_prompt'),
    path('api/prompts/delete/<int:prompt_id>/', views.delete_prompt, name='delete_prompt'),
    path('api/prompts/toggle-status/<int:prompt_id>/', views.toggle_status, name='toggle_status'),
]
