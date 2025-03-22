from django.urls import path
from .views import start_crawl, view_links_by_domain, add_link, crawl, get_links, delete_link

urlpatterns = [
    path('crawl/', start_crawl, name='start_crawl'),  # This must be present!
    path('crawling/', crawl, name='crawling'),
    path('links/<str:domain>/', view_links_by_domain, name='view_links_by_domain'),
    path('api/add_link/', add_link, name='add_link'),
    path("api/get_links/", get_links, name="get_links"),
    path('api/delete_link/', delete_link, name='delete_link'),
]
