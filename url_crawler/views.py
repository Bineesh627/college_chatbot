from django.shortcuts import render
from django.http import JsonResponse
from url_crawler.utils.crawler import crawl_website
from .models import CrawledURL, CrawlQueue
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from urllib.parse import urlparse
from django.utils.timezone import now
import json

def crawl(requests):
    return render(requests, 'url_crawler/crawl.html')

def add_scraped_link(url):
    """Insert link only if its domain is not already in the database."""
    parsed_url = urlparse(url)
    domain = parsed_url.netloc  # Extract domain

    # Check if the domain already exists
    if CrawlQueue.objects.filter(domain=domain).exists():
        print(f"Domain {domain} already exists. Skipping: {url}")
        return {"status": "exists", "message": "Domain already exists", "url": url}

    # Insert new link
    scraped_link = CrawlQueue.objects.create(
        link=url,
        domain=domain,
        status="pending",  # Default status
        is_new=True
    )
    
    print(f"Added new link: {scraped_link.link} (Domain: {domain})")
    return {"status": "added", "message": "New link added", "url": url}

def get_links(request):
    """API to return all stored URLs."""
    links = CrawlQueue.objects.all().values("id", "link", "status", "last_updated")
    return JsonResponse({"urls": list(links)}, safe=False)

@csrf_exempt
def delete_link(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            url = data.get("url")
            link = get_object_or_404(CrawlQueue, link=url)
            link.delete()
            return JsonResponse({"status": "deleted", "message": "Link deleted", "url": url})
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
    return JsonResponse({"error": "Invalid request method"}, status=405)

@csrf_exempt
def add_link(request):
    """API endpoint to add a link if the domain is not already in the database."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            url = data.get("url")

            if not url:
                return JsonResponse({"error": "URL is required"}, status=400)

            result = add_scraped_link(url)

            # Return the updated list of links
            all_links = list(CrawlQueue.objects.values("id", "link", "status", "updated_at"))  
            return JsonResponse({"status": result["status"], "message": result["message"], "urls": all_links})

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

    return JsonResponse({"error": "Invalid request method"}, status=405)

def start_crawl(request):
    base_url = request.GET.get("url")
    if not base_url:
        return JsonResponse({"error": "Please provide a URL"}, status=400)

    # Fetch the entry from DB and update the status
    link_entry = get_object_or_404(CrawlQueue, link=base_url)
    link_entry.status = "crawling"
    link_entry.save(update_fields=["status", "last_updated"])  # Save the updated status

    # Simulate crawling process
    try:
        crawl_website(base_url)  # Your crawling function
        link_entry.status = "completed"
    except Exception as e:
        link_entry.status = "failed"
    
    link_entry.last_updated = now()
    link_entry.save(update_fields=["status", "last_updated"])  # Save the final status

    return JsonResponse({"message": f"Crawling completed for {base_url}", "status": link_entry.status})

def view_links_by_domain(request, domain):
    links_list = CrawledURL.objects.filter(domain=domain).order_by('-first_crawled')

    rows_per_page = request.GET.get('rows', 50)
    if str(rows_per_page) not in ["50", "100"]:
        rows_per_page = 50

    paginator = Paginator(links_list, int(rows_per_page))
    page_number = request.GET.get('page')
    links = paginator.get_page(page_number)

    return render(request, 'url_crawler/view_crawl.html', {'links': links, 'rows_per_page': int(rows_per_page), 'domain': domain})
