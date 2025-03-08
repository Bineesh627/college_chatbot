from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'), # Home page
    path('qa_workflow/', views.qa_workflow, name='qa_workflow'), # Main workflow view
    path('add_prompt/', views.add_prompt, name='add_prompt'),
    path('view_prompt/', views.view_prompt, name='view_prompt'),
    path('edit_prompt/<int:prompt_id>/', views.edit_prompt, name='edit_prompt'),
    path('delete_prompt/<int:prompt_id>/', views.delete_prompt, name='delete_prompt'),
]