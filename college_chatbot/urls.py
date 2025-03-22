from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('prompt_management.urls')),
    # path('', include('webpage_processor.urls')),
    path('', include('url_crawler.urls')),
    path('', include('college_interface.urls')),
    path('', include('chatbot.urls')),
    path('', include('pdf_data.urls')),
    path('', include('dashboard.urls')),
    path('', include('admin_panel.urls')),
    path('', include('settings.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += staticfiles_urlpatterns()
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += staticfiles_urlpatterns()