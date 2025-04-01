from django.db import models
from django.utils.timezone import now

class DashboardAnalytics(models.Model):
    analytics_id = models.AutoField(primary_key=True)  # Unique identifier for each analytics entry
    date = models.DateField(default=now, unique=True)  # Stores daily analytics
    total_conversations = models.IntegerField(default=0)
    total_documents = models.IntegerField(default=0)
    embedding_queue = models.IntegerField(default=0)
    active_crawlers = models.IntegerField(default=0)

    class Meta:
        db_table = 'dashboard_analytics'
        ordering = ['-date']

    def __str__(self):
        return f"Analytics for {self.date}"