from django.db import models

class ChatSession(models.Model):
    session_id = models.CharField(max_length=40, primary_key=True, editable=False) #changed to charfield
    conversation_history = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.session_id #changed to self.session_id

    class Meta:
        db_table = 'chatbot_chatsession'
        indexes = [
            models.Index(fields=['session_id']),
        ]