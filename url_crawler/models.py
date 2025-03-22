from django.db import models

# Create your models here.
class CrawlQueue(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('crawling', 'Crawling'),
        ('completed', 'Completed'),
        ('failed', 'Failed')
    ]

    link = models.URLField(unique=True)
    domain = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')  # Crawling status
    http_status = models.IntegerField(default=200)  # HTTP response code
    is_new = models.BooleanField(default=True)  # Marks new links
    first_crawled = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "crawl_queue"
        
class CrawledURL(models.Model):
    link = models.URLField(unique=True)
    domain = models.CharField(max_length=255)
    status = models.IntegerField(default=200)  # HTTP status code
    is_new = models.BooleanField(default=True)  # Marks new links
    first_crawled = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "crawled_url"