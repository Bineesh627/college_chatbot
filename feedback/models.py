from django.db import models
from chatbot.models import ChatSession

class ChatFeedback(models.Model):
    feedback_id = models.AutoField(primary_key=True)
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='feedbacks')
    timestamp = models.DateTimeField(auto_now_add=True)
    query = models.TextField()
    chatbot_response = models.TextField()
    thumbs_up = models.BooleanField(null=True, blank=True) # Nullable to handle cases where no feedback given.
    feedback_text = models.TextField(null=True, blank=True)
    context = models.JSONField(null=True, blank=True) # Store context as JSON
    viewed_context = models.BooleanField(default=False)
    topic = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"Feedback for {self.session.session_id} - {self.timestamp}"

    class Meta:
        db_table = 'chatbot_chatfeedback'
        indexes = [
            models.Index(fields=['session']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['topic']),
        ]