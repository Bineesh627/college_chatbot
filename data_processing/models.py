from django.db import models

class CrawledURL(models.Model):
    crawl_id = models.AutoField(primary_key=True)
    source_url = models.TextField()
    status_code = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'crawled_url'

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
    crawled_url = models.ForeignKey(
        CrawledURL, on_delete=models.CASCADE, related_name='document_chunks',
        null=True, blank=True
    )
    document = models.ForeignKey(
        UploadedDocument, on_delete=models.CASCADE, related_name='document_chunks',
        null=True, blank=True
    )
    content = models.TextField()
    embedding = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'document_chunks'