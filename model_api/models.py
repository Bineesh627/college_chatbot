from django.db import models

class ModelSettings(models.Model):
    model_id = models.AutoField(primary_key=True)
    aws_region = models.CharField(max_length=100)
    api_key = models.CharField(max_length=255)
    secret_key = models.CharField(max_length=255)
    model_version = models.CharField(max_length=50, default="LLaMA 3.3 70B")
    temperature = models.FloatField(default=0.5)
    max_tokens = models.IntegerField(default=2048)
    context_window = models.IntegerField(default=4096)

    class Meta:
        db_table = 'model_settings'
