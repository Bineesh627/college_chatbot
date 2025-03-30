import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor
from url_crawler.models import CrawledURL
from pdf_data.models import UploadedDocument  # Ensure this model is imported
from django.utils.timezone import now

IGNORED_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.gif', '.svg', 
                      '.mp4', '.avi', '.mov', '.wmv', '.mp3', '.wav', 
                      '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.zip')

IGNORED_PATHS = ('/cdn-cgi/', '/email-protection', '/wp-content/', '/wp-login.php')

MAX_THREADS = 10  

def normalize_url(url):
    """ Normalize URL by removing fragments (#) and trailing slashes. """
    parsed_url = urlparse(url)
    clean_url = parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path
    return clean_url.rstrip('/')  # Remove trailing slashes

def crawl_website(base_url):
    """ Crawl until no new links are found. """
    visited = set()
    queue = [normalize_url(base_url)]  # Use a queue to keep track of links to visit

    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        while queue:
            new_links = []
            future_tasks = []

            for url in queue:
                if url in visited:
                    continue  # Skip already visited links

                visited.add(url)
                domain = urlparse(url).netloc
                path = urlparse(url).path

                if any(ignored in path for ignored in IGNORED_PATHS):
                    print(f"Skipping unwanted path: {url}")
                    continue

                # Crawl the page
                future_tasks.append(executor.submit(fetch_and_extract_links, url, domain, new_links, visited))

            # Wait for all threads to complete
            for future in future_tasks:
                future.result()

            # Add new links to the queue for further crawling
            queue = list(set(new_links) - visited)

    print("✅ Crawling Completed!")

def fetch_and_extract_links(url, domain, new_links, visited):
    """ Fetch page content and extract links including PDFs. """
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"}
        response = requests.get(url, headers=headers, timeout=5)
        response.encoding = response.apparent_encoding  # Detect and set proper encoding
        status_code = response.status_code

        if status_code != 200:
            return

        soup = BeautifulSoup(response.text, "html.parser")

        # Save or update the link in the database
        link_obj, created = CrawledURL.objects.get_or_create(source_url=url, defaults={
            "domain": domain,
            "status_code": status_code,
            "is_new": True,
        })
        if not created:
            link_obj.status_code = status_code
            link_obj.is_new = False
            link_obj.save()

        # Extract links from the page
        for link in soup.find_all("a", href=True):
            href = link.get("href")
            full_url = normalize_url(urljoin(url, href))

            if urlparse(full_url).netloc != domain or \
               any(ignored in urlparse(full_url).path for ignored in IGNORED_PATHS):
                continue

            if full_url.lower().endswith(".pdf"):
                process_and_store_pdf(full_url)
                continue

            if full_url not in visited and not full_url.lower().endswith(IGNORED_EXTENSIONS):
                new_links.append(full_url)
    
    except requests.exceptions.RequestException:
        return

def process_and_store_pdf(pdf_url):
    """ Process and store PDF links in the UploadedDocument model. """
    try:
        pdf_title = pdf_url.split('/')[-1].replace('.pdf', '')  # Extract filename without .pdf extension
        UploadedDocument.objects.get_or_create(
            document_url=pdf_url,
            defaults={
                "document_title": pdf_title,
                "file_type": "pdf",
                "created_at": now(),
            }
        )
        print(f"📄 Stored PDF: {pdf_title} -> {pdf_url}")
    except Exception as e:
        print(f"❌ Error storing PDF {pdf_url}: {e}")