from django.db import models

class SystemPrompt(models.Model):
    prompt_id = models.AutoField(primary_key=True)
    prompt_name = models.CharField(max_length=255, help_text="Prompt name (e.g., 'Default Prompt').")
    prompt_text = models.TextField(help_text="System prompt text content.")
    is_active = models.BooleanField(default=True, help_text="Is this prompt currently active?")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp of prompt creation.")
    updated_at = models.DateTimeField(auto_now=True, help_text="Timestamp of last prompt update.")

    class Meta:
        db_table = 'system_prompts'
