from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta, datetime, date # Import date
from collections import Counter, defaultdict
import logging
from .models import ChatbotFeedback

# Setup logger for this view file
logger = logging.getLogger('custom_logger') # Use the name you defined

def feedback(request):
    return render(request, 'feedback/feedback.html')

def feedback_api(request):
    filter_param = request.GET.get('filter', 'all')

    if filter_param == 'positive':
        feedback_entries = ChatbotFeedback.objects.filter(thumbs_up__in=[True])
    elif filter_param == 'negative':
        feedback_entries = ChatbotFeedback.objects.filter(thumbs_up__in=[False])
    else:
        feedback_entries = ChatbotFeedback.objects.all()

    # Apply ordering and limit *after* filtering
    feedback_entries = feedback_entries.order_by('-timestamp')[:20]

    data = []
    for entry in feedback_entries:
        formatted_time = str(entry.timestamp) # Or simply convert to string if sufficient

        data.append({
            "feedback_id": entry.feedback_id,
            "topic": entry.topic,
            "query": entry.query,
            "response": entry.response,
            "thumbs_up": entry.thumbs_up,
            "feedback": entry.feedback,
            "time": entry.timestamp, # Use the formatted/string version
            # "timestamp": formatted_time
        })

    return JsonResponse({"data": data})

# --- API View: Calculate Response Accuracy Card (No changes needed here) ---
def get_response_accuracy(request):
    logger.info("API call received: get_response_accuracy")
    try:
        today = timezone.now().date()
        start_of_week = today - timedelta(days=today.weekday())
        start_of_last_week = start_of_week - timedelta(days=7)
        end_of_last_week = start_of_week - timedelta(days=1)
        logger.debug(f"Accuracy Target Dates: This week >= {start_of_week}, Last week {start_of_last_week} to {end_of_last_week}")

        potential_feedback = ChatbotFeedback.objects.filter(
            timestamp__gte=datetime.combine(start_of_last_week, datetime.min.time())
            # Add timezone.make_aware if needed
        ).order_by('timestamp')
        logger.debug(f"Fetched {potential_feedback.count()} potential records since start of last week.")

        this_week_feedback = []
        last_week_feedback = []

        for entry in potential_feedback:
            if not entry.timestamp or not isinstance(entry.timestamp, (datetime, timezone.datetime)):
                logger.warning(f"Skipping entry {entry.pk} due to invalid timestamp during Python filtering.")
                continue
            entry_date = entry.timestamp.date()
            if entry_date >= start_of_week:
                this_week_feedback.append(entry)
            elif entry_date >= start_of_last_week and entry_date <= end_of_last_week:
                last_week_feedback.append(entry)

        total_this_week = len(this_week_feedback)
        positive_this_week = sum(1 for entry in this_week_feedback if entry.thumbs_up is True)
        logger.debug(f"This week counts (Python filtered): Total={total_this_week}, Positive={positive_this_week}")

        total_last_week = len(last_week_feedback)
        positive_last_week = sum(1 for entry in last_week_feedback if entry.thumbs_up is True)
        logger.debug(f"Last week counts (Python filtered): Total={total_last_week}, Positive={positive_last_week}")

        response_accuracy = (positive_this_week / total_this_week * 100) if total_this_week > 0 else 0.0
        last_week_accuracy = (positive_last_week / total_last_week * 100) if total_last_week > 0 else 0.0

        change_percentage = 0.0
        if last_week_accuracy > 0:
            change_percentage = ((response_accuracy - last_week_accuracy) / last_week_accuracy) * 100

        response_data = {
            'response_accuracy': round(response_accuracy, 2),
            'change_percentage': round(change_percentage, 2)
        }
        logger.info("Response accuracy calculated successfully (using Python filtering).")
        return JsonResponse(response_data)

    except Exception as e:
        logger.error(f"CRITICAL Error in get_response_accuracy: {e}", exc_info=True)
        return JsonResponse(
            {'error': 'Failed to calculate response accuracy', 'details': str(e)},
            status=500
        )

# --- API View: Get Common Topics (No changes needed here) ---
def get_common_topics(request):
    logger.info("API call received: get_common_topics")
    try:
        feedback_topics = ChatbotFeedback.objects.values_list('topic', flat=True)
        valid_topics = [topic for topic in feedback_topics if topic]
        total_feedback = len(valid_topics)
        logger.debug(f"Total valid topics counted: {total_feedback}")

        if total_feedback == 0:
            logger.info("No valid topics found.")
            return JsonResponse({'common_topics': []})

        topic_counts = Counter(valid_topics)
        common_topics_data = [
            {
                'topic': topic,
                'percentage': round((count / total_feedback) * 100, 2)
            }
            for topic, count in topic_counts.items()
        ]
        common_topics_data.sort(key=lambda x: x['percentage'], reverse=True)
        response_data = {'common_topics': common_topics_data}
        logger.info("Common topics calculated successfully.")
        return JsonResponse(response_data)

    except Exception as e:
        logger.error(f"CRITICAL Error in get_common_topics: {e}", exc_info=True)
        return JsonResponse(
            {'error': 'Failed to calculate common topics', 'details': str(e)},
            status=500
        )

# --- API View: Get Quality Trends (Simplified for Accuracy Only) ---
def get_quality_trends(request):
    logger.info("API call received: get_quality_trends (Accuracy Only)") # Updated log
    try:
        today = timezone.now().date()
        past_week_dates = [(today - timedelta(days=i)) for i in range(6, -1, -1)]
        trend_start_date = past_week_dates[0]
        logger.debug(f"Accuracy Trend Target Dates: {trend_start_date} to {today}") # Updated log

        potential_entries = ChatbotFeedback.objects.filter(
            timestamp__gte=datetime.combine(trend_start_date, datetime.min.time())
            # Add timezone.make_aware if needed
        ).values('timestamp', 'thumbs_up', 'pk') # No need for satisfaction field now
        logger.debug(f"Fetched {potential_entries.count()} potential entries for accuracy trend analysis.") # Updated log

        # Aggregate Data Per Day (Only need total and positive)
        daily_data = defaultdict(lambda: {'total': 0, 'positive': 0})

        for entry in potential_entries:
            ts = entry.get('timestamp')
            pk = entry.get('pk', 'N/A')

            if not ts or not isinstance(ts, (datetime, timezone.datetime)):
                logger.warning(f"Skipping entry {pk} due to invalid timestamp during Python aggregation.")
                continue

            day = ts.date()

            if day >= trend_start_date and day <= today:
                 daily_data[day]['total'] += 1
                 if entry.get('thumbs_up') is True:
                     daily_data[day]['positive'] += 1

        # Prepare Data for Chart (Only accuracy needed)
        accuracy_data_points = []
        chart_labels = []

        for day_date in past_week_dates:
            chart_labels.append(day_date.strftime('%a'))
            day_stats = daily_data[day_date]
            if day_stats['total'] > 0:
                daily_accuracy = round((day_stats['positive'] / day_stats['total']) * 100, 2)
                accuracy_data_points.append(daily_accuracy)
            else:
                accuracy_data_points.append(0.0)

        logger.debug(f"Trend Labels: {chart_labels}")
        logger.debug(f"Trend Accuracy Data: {accuracy_data_points}")

        # Return only accuracy data in JSON
        response_data = {
            'labels': chart_labels,
            'accuracy_data': accuracy_data_points,
        }
        logger.info("Accuracy trends calculated successfully.") # Updated log
        return JsonResponse(response_data)

    except Exception as e:
        logger.error(f"CRITICAL Error in get_quality_trends: {e}", exc_info=True)
        return JsonResponse(
            {'error': 'Failed to calculate quality trends', 'details': str(e)},
            status=500
        )

def get_total_responses(request):
    """
    Counts the total number of feedback entries in the last 7 days.
    """
    logger.info("API call received: get_total_responses")
    try:
        # --- Date Calculation ---
        today = timezone.now().date()
        start_date = today - timedelta(days=6) # Today + previous 6 days = 7 days total
        logger.debug(f"Total Responses Date Range: >= {start_date}")

        # --- Query Database (using timestamp >= start_date) ---
        # Using Python filtering approach consistent with other views
        potential_entries = ChatbotFeedback.objects.filter(
            timestamp__gte=datetime.combine(start_date, datetime.min.time())
            # Add timezone.make_aware if needed
        ) # No specific fields needed, just the count

        # Filter in Python (more accurate if timestamps aren't perfectly aligned with dates)
        count = 0
        for entry in potential_entries:
             if not entry.timestamp or not isinstance(entry.timestamp, (datetime, timezone.datetime)):
                 continue # Skip invalid timestamps
             entry_date = entry.timestamp.date()
             if entry_date >= start_date and entry_date <= today:
                 count += 1

        # --- Alternative: Direct DB Count (Simpler if date filtering worked reliably) ---
        # If you *trust* the DB __gte filter after combining date/time:
        # count = ChatbotFeedback.objects.filter(
        #    timestamp__gte=datetime.combine(start_date, datetime.min.time()) # Add tz if needed
        # ).count()
        # logger.debug(f"Total responses count (DB): {count}")

        logger.info(f"Total responses calculated successfully: {count}")
        return JsonResponse({'total_responses': count})

    except Exception as e:
        logger.error(f"CRITICAL Error in get_total_responses: {e}", exc_info=True)
        return JsonResponse(
            {'error': 'Failed to calculate total responses', 'details': str(e)},
            status=500
        )