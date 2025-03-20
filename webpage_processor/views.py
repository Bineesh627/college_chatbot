import logging
from apscheduler.schedulers.background import BackgroundScheduler
from django.utils.timezone import now
from webpage_processor.utils.content_processing import process_content_view

# Configure logging
logger = logging.getLogger('custom_logger')

def scheduled_content_processing():
    """ Function to process content every minute """
    logger.info(f"Scheduled task started at {now()}")
    process_content_view(None)  # Call function without request
    logger.info(f"Scheduled task completed at {now()}")

def start_scheduler():
    """ Start APScheduler """
    scheduler = BackgroundScheduler()
    scheduler.add_job(scheduled_content_processing, 'interval', hours=10, id="scheduled_content_processing", replace_existing=True, max_instances=1)  # Runs every 1 minute
    scheduler.start()
    logger.info("APScheduler started...")
