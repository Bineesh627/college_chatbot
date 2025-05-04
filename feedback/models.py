from django.db import models
from chatbot.models import ChatSession

class ChatbotFeedback(models.Model):
    feedback_id = models.AutoField(primary_key=True)  # Explicit Primary Key
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name="feedback")  # Added ForeignKey
    topic = models.CharField(max_length=255)
    query = models.TextField()
    response = models.TextField()
    thumbs_up = models.BooleanField()  # True = Positive, False = Negative
    feedback = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.topic} - {self.query[:50]}"

    class Meta:
        db_table = 'chat_feedback'
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['topic']),
        ]