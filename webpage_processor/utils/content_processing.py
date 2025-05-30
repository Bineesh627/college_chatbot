import hashlib
import requests
import logging
import re
from bs4 import BeautifulSoup
from django.db import transaction
from django.http import JsonResponse
from pdf_data.models import DocumentChunks
from url_crawler.models import CrawledURL
from model_api.views import generate_embeddings, chunk_content

logger = logging.getLogger('custom_logger')

def decode_email(encoded_email):
    try:
        decoded = ''
        hex_value = int(encoded_email[:2], 16)
        for i in range(2, len(encoded_email), 2):
            decoded += chr(int(encoded_email[i:i+2], 16) ^ hex_value)
        logging.info(f"Decoded email successfully: {decoded}")
        return decoded
    except Exception:
        logging.error(f"Error decoding email: {encoded_email}, Error: {e}")
        return None

def clean(text):
    symbol_pattern = r"[^\w\s]"
    text = re.sub(symbol_pattern, " ", text)
    text = re.sub(r'\s+', ' ', text.replace("\n", " ").replace("\t", " ")).strip().lower()
    return text

def get_content(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Remove unwanted tags
        for tag in soup(['header', 'footer', 'button', 'script']):
            tag.decompose()
        for tag in soup.find_all(class_=["bottom-sec", "bottom-sec1", "header", "newses2", "banner-wrapper", "gallery_sec", "read_more2", "read_more", "read_more1"]):
            tag.decompose()
        for tag in soup.find_all('div', id=["accordion", "side_nav", "nt-example1-container"]):
            tag.decompose()

        body_content = soup.body
        if not body_content:
            return ""

        body_text = body_content.get_text(separator=' ', strip=True)
        cleaned_text = clean(body_text)

        # Decode and replace encoded emails
        for email_element in soup.find_all('a', class_='__cf_email__'):
            encoded_email = email_element.get('data-cfemail')
            if encoded_email:
                decoded_email = decode_email(encoded_email)
                if decoded_email:
                    cleaned_text = cleaned_text.replace(email_element.get_text(), decoded_email)
                    cleaned_text = cleaned_text.replace('email protected', decoded_email)

        return cleaned_text

    except requests.exceptions.ConnectionError:
        logging.error(f"Network error: Unable to connect to {url}. Check DNS or network settings.")
        return None
    except requests.exceptions.Timeout:
        logging.error(f"Timeout error: {url} took too long to respond.")
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching URL {url}: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error processing {url}: {e}")
        return None

def hash_chunk(chunk):
    """Generates a hash for a text chunk."""
    return hashlib.sha256(chunk.encode()).hexdigest()

def update_database_django_orm(url, crawled_url_instance):
    """Updates the database with extracted and embedded content."""
    content = get_content(url)
    if not content:
        logger.warning(f"No valid content extracted from {url}")
        return

    new_chunks = chunk_content(content)
    new_hashes = {hash_chunk(chunk): chunk for chunk in new_chunks}

    # Fetch existing chunks from DB
    existing_chunks = DocumentChunks.objects.filter(crawled_url=crawled_url_instance)
    old_hashes = {chunk.hash: (chunk.chunk_id, chunk.embedding) for chunk in existing_chunks}

    to_add = []
    to_delete = []

    for chunk_hash, chunk_text in new_hashes.items():
        if chunk_hash not in old_hashes:
            embedding = generate_embeddings(chunk_text)
            to_add.append(DocumentChunks(
                crawled_url=crawled_url_instance, content=chunk_text, hash=chunk_hash, embedding=embedding
            ))
        else:
            chunk_id, embedding = old_hashes[chunk_hash]
            if not embedding:
                new_embedding = generate_embeddings(chunk_text)
                DocumentChunks.objects.filter(chunk_id=chunk_id).update(embedding=new_embedding)

    to_delete = [chunk_id for chunk_hash, (chunk_id, _) in old_hashes.items() if chunk_hash not in new_hashes]

    with transaction.atomic():
        DocumentChunks.objects.filter(chunk_id__in=to_delete).delete()
        DocumentChunks.objects.bulk_create(to_add)

    logger.info(f"Processed {url} - Added: {len(to_add)}, Removed: {len(to_delete)}")

def process_content_view(request, url=None):
    """Django view to process content."""
    logger.info("Starting content processing...")

    processed_count = 0
    error_count = 0

    urls = [url] if url else list(CrawledURL.objects.filter(status_code=200).values_list('source_url', flat=True))

    for current_url in urls:
        try:
            crawled_url_instance, _ = CrawledURL.objects.get_or_create(
                source_url=current_url, defaults={'status_code': 200}
            )
            update_database_django_orm(current_url, crawled_url_instance)
            processed_count += 1
            logger.info(f"Successfully processed: {current_url}")
        except Exception as e:
            logger.error(f"Error processing URL {current_url}: {e}")
            error_count += 1

    return JsonResponse({'status': "success" if error_count == 0 else "error", 'processed_count': processed_count, 'error_count': error_count})
