from django.apps import AppConfig
import threading

class ContentConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "webpage_processor"

    def ready(self):
        """ Start the scheduler only after Django is fully initialized """
        from webpage_processor.views import start_scheduler  # Import inside the function
        if not hasattr(self, 'scheduler_started'):
            self.scheduler_started = True  # Ensure it runs only once
            thread = threading.Thread(target=start_scheduler, daemon=True)
            thread.start()
