from django.db import models

class CrawledURL(models.Model):
    crawl_id = models.AutoField(primary_key=True)
    source_url = models.TextField()  # Crawled page URL
    status_code = models.IntegerField()  # HTTP response status (e.g., 200, 404)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'crawled_url'

class DocumentChunks(models.Model):
    chunk_id = models.AutoField(primary_key=True)
    crawled_url = models.ForeignKey(CrawledURL, on_delete=models.CASCADE, related_name='document_chunks') 
    content = models.TextField()  # Plain text content of the chunk
    embedding = models.JSONField() # Vector embedding
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'document_chunks'