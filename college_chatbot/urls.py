from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('data_processing.urls')),
    # path('', include('chatbot_app.urls')),
    path('qa/', include('qa_app.urls')),
]
