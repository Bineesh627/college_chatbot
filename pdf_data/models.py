from django.db import models
from url_crawler.models import CrawledURL

class UploadedDocument(models.Model):
    document_id = models.AutoField(primary_key=True)
    document_title = models.CharField(max_length=255)
    document_url = models.URLField()
    file_path = models.FileField(upload_to='documents/')
    pdf_hash = models.CharField(max_length=64, null=True, blank=True)
    file_type = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'uploaded_document'

class DocumentChunks(models.Model):
    chunk_id = models.AutoField(primary_key=True)
    # A chunk can belong to either a crawled URL OR an uploaded document
    crawled_url = models.ForeignKey(
        CrawledURL, on_delete=models.CASCADE, related_name='document_chunks',
        null=True, blank=True  # ✅ Allows NULL for uploaded files
    )
    document = models.ForeignKey(
        UploadedDocument, on_delete=models.CASCADE, related_name='document_chunks',
        null=True, blank=True  # ✅ Allows NULL for crawled pages
    )
    content = models.TextField()
    hash = models.CharField(max_length=64, unique=True) #using hash as unique identifier
    embedding = models.JSONField(null=True, blank=True) # Vector embedding
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'document_chunks'