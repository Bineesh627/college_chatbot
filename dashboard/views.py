from django.shortcuts import render
from admin_panel.decorators import admin_required
import json
from django.http import JsonResponse
from chatbot.models import ChatSession
from pdf_data.models import DocumentChunks
from url_crawler.models import CrawlQueue
from datetime import datetime, timedelta
from django.utils.timezone import now, make_aware  # Import make_aware
from .models import DashboardAnalytics
from django.views.decorators.csrf import csrf_exempt

@admin_required
def dashboard(request):
    return render(request, 'dashboard/dashboard.html')

@admin_required
def monitoring(request):
    return render(request, 'dashboard/monitoring.html')

def calculate_trend(current, previous):
    if previous == 0:
        return 100 if current > 0 else 0
    return round(((current - previous) / previous) * 100, 2)

@csrf_exempt
def analytics_api(request):
    try:
        print("analytics_api view START")
        today = now().date()
        print(f"Today's date: {today}")
        analytics, created = DashboardAnalytics.objects.get_or_create(date=today)
        print(f"DashboardAnalytics object: {analytics}, Created: {created}")

        # Fetch values
        print("Fetching total_conversations...")
        analytics.total_conversations = ChatSession.objects.count()
        print(f"Total Conversations: {analytics.total_conversations}")

        print("Fetching total_documents...")
        analytics.total_documents = DocumentChunks.objects.count()
        print(f"Total Documents: {analytics.total_documents}")

        print("Fetching embedding_queue...")
        analytics.embedding_queue = DocumentChunks.objects.filter(embedding__isnull=True).count()
        print(f"Embedding Queue: {analytics.embedding_queue}")

        print("Fetching active_crawlers...")
        analytics.active_crawlers = CrawlQueue.objects.filter(status='crawling').count()
        print(f"Active Crawlers: {analytics.active_crawlers}")
        analytics.save()
        print("Analytics object saved.")

        # --- Timezone-Aware Conversation Trends Query ---
        print("Fetching conversation_trends...")
        conversation_trends = []
        for i in range(7):
            date = today - timedelta(days=i)
            start_of_day_naive = datetime.combine(date, datetime.min.time())  # Naive datetime
            end_of_day_naive = datetime.combine(date, datetime.max.time())    # Naive datetime
            start_of_day = make_aware(start_of_day_naive) # Make timezone-aware
            end_of_day = make_aware(end_of_day_naive)     # Make timezone-aware
            count = ChatSession.objects.filter(created_at__gte=start_of_day, created_at__lte=end_of_day).count()
            conversation_trends.append({'date': date.strftime('%Y-%m-%d'), 'count': count})
        conversation_trends.reverse()
        print(f"Conversation Trends: {conversation_trends}")

        # --- Timezone-Aware Previous Week Data Queries ---
        print("Fetching previous week conversations...")
        prev_week_start_date = today - timedelta(days=14)
        prev_week_end_date = today - timedelta(days=7)
        prev_week_start_datetime_naive = datetime.combine(prev_week_start_date, datetime.min.time()) # Naive
        prev_week_end_datetime_naive = datetime.combine(prev_week_end_date, datetime.max.time())   # Naive
        prev_week_start_datetime = make_aware(prev_week_start_datetime_naive) # Make aware
        prev_week_end_datetime = make_aware(prev_week_end_datetime_naive)     # Make aware

        prev_week_conversations = ChatSession.objects.filter(
            created_at__gte=prev_week_start_datetime, created_at__lte=prev_week_end_datetime
        ).count()
        print(f"Previous Week Conversations: {prev_week_conversations}")

        print("Fetching previous week documents...")
        prev_week_documents = DocumentChunks.objects.filter(
            created_at__gte=prev_week_start_datetime, created_at__lte=prev_week_end_datetime
        ).count()
        print(f"Previous Week Documents: {prev_week_documents}")

        conversation_trend = calculate_trend(analytics.total_conversations, prev_week_conversations)
        document_trend = calculate_trend(analytics.total_documents, prev_week_documents)

        # System status
        print("Setting service_statuses...")
        service_statuses = [
            {'name': 'Embedding Service', 'status': 'operational' if analytics.embedding_queue < 10 else 'down'},
            {'name': 'Crawler Service', 'status': 'operational' if analytics.active_crawlers > 0 else 'down'},
            {'name': 'Database Connection', 'status': 'operational'}
        ]
        print(f"Service Statuses: {service_statuses}")

        print("Returning JsonResponse...")
        return JsonResponse({
            'totalConversations': analytics.total_conversations,
            'totalDocuments': analytics.total_documents,
            'embeddingQueue': analytics.embedding_queue,
            'activeCrawlers': analytics.active_crawlers,
            'conversationTrends': conversation_trends,
            'trends': {
                'conversations': conversation_trend,
                'documents': document_trend,
            },
            'serviceStatuses': service_statuses
        })

    except Exception as e:
        print(f"Exception caught: {e}")
        return JsonResponse({'error': str(e)}, status=500)
    finally:
        print("analytics_api view END")