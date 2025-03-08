from django.shortcuts import render
from .models import CrawledURL, DocumentChunks
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_community.docstore.document import Document
from langchain_aws import BedrockEmbeddings
import requests
from bs4 import BeautifulSoup
import json  # Import json module
import re

def data_source(request):
    return render(request, 'data_processing/data_source.html')

def decode_email(encoded_email):
    decoded = ''
    hex_value = int(encoded_email[:2], 16)
    for i in range(2, len(encoded_email), 2):
        decoded += chr(int(encoded_email[i:i+2], 16) ^ hex_value)
    return decoded

def clean_and_extract_data(url):
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

        # Extract body text
        body_content = soup.body
        if not body_content:
            return None

        body_text = body_content.get_text(separator=' ', strip=True)
        symbol_pattern = r"[^\w\s]"
        cleaned_text = re.sub(symbol_pattern, " ", body_text)
        cleaned_text = re.sub(r'&nbsp;?', ' ', cleaned_text) #remove &nbsp here.
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
        cleaned_text = cleaned_text.lower()

        # Decode and replace emails
        email_elements = soup.find_all('a', class_='__cf_email__')
        decoded_emails = []
        for email_element in email_elements:
            encoded_email = email_element['data-cfemail']
            decoded_email = decode_email(encoded_email)
            decoded_emails.append(decoded_email)

            # Replace encoded emails in the text
            cleaned_text = cleaned_text.replace(email_element.get_text(), decoded_email)

        # Replace '[email protected]' with the first decoded email (if available)
        if decoded_emails:
            cleaned_text = cleaned_text.replace('email protected', decoded_emails[0])

        # Return a list containing a Langchain Document object
        return [Document(page_content=cleaned_text, metadata={"source": url})] # Correct return type

    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

def start_content(request):
    message = "" # Define message variable

    # Load URLs with status_code 200 directly and convert to Python list
    urls_queryset = CrawledURL.objects.filter(status_code=200).values_list('source_url', flat=True)
    urls = list(urls_queryset)

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=80,
        length_function=len,
        is_separator_regex=False,
    )

    for url in urls:
        try:
            # Load document for a single URL using your custom function
            extracted_document_list = clean_and_extract_data(url) # Renamed docs to extracted_document_list

            if not extracted_document_list: # Check for empty list (or None)
                print(f"No documents loaded for URL: {url}")
                message += f"No documents loaded for URL: {url}<br>"
                continue  # Skip to the next URL if no documents are loaded

            # Split the document into chunks - now using correct input type
            chunks = text_splitter.split_documents(extracted_document_list) # Pass the list of Documents
            print(chunks)

            # Get the CrawledURL instance for this URL to link chunks
            crawled_url_instance = CrawledURL.objects.get(source_url=url)

            for chunk in chunks:
                cleaned_content = chunk.page_content # Extract cleaned content from Document object
                print(cleaned_content)

                # Use update_or_create to prevent duplicates - Uncommented to store data
                DocumentChunks.objects.update_or_create(
                    crawled_url=crawled_url_instance,
                    content=cleaned_content,
                    defaults={'embedding': {}}  # Embeddings will be added later
                )
                print(f"Stored chunk for URL: {url}") # Indicate storage
            message += f"Processed and stored chunks for URL: {url}<br>" # Update message
            print(f"Processed and stored chunks for URL: {url}")


        except CrawledURL.DoesNotExist:
            print(f"CrawledURL instance not found for URL: {url}")
            message += f"CrawledURL instance not found for URL: {url}<br>"
        except Exception as e:
            print(f"Error processing URL {url}: {e}")
            message += f"Error processing URL {url}: {e}<br>"

    message += "<br>Content processing completed." # Final message
    return render(request, 'data_processing/content_process.html', {'message': message}) # Pass message to template

def get_embedding_function():
    embeddings = BedrockEmbeddings(
        credentials_profile_name="default", region_name="us-east-1"
    )
    # embeddings = OllamaEmbeddings(model="nomic-embed-text") # Use this for Ollama embeddings
    # embeddings = OllamaEmbeddings(model="llama3.2", base_url="http://localhost:11434") # Use this for local Ollama embeddings
    return embeddings


def start_embedding(request):   
    embedding_model = get_embedding_function()

    # Fetch all DocumentChunks records from MongoDB
    document_chunks = DocumentChunks.objects.all()

    updated_count = 0
    error_count = 0

    for chunk_obj in document_chunks:  # Iterate through DocumentChunks objects directly
        try:
            content_to_embed = chunk_obj.content
            print(content_to_embed)

            # Generate embedding for the content
            embedding_vector = embedding_model.embed_query(content_to_embed)
            print(embedding_vector)

            # Convert embedding vector to JSON string (or directly store as Python list/dict if JSONField handles it)
            # **Important:** JSONField in Django can store Python dictionaries and lists directly.
            # No need to manually convert to JSON string unless you have a specific reason.
            # Let's store it as a Python list/dict (which JSONField will serialize)
            embedding_to_store = embedding_vector  # or {'vector': embedding_vector} if you want a dict structure

            # Update the embedding field of the *existing* DocumentChunks object
            chunk_obj.embedding = embedding_to_store
            chunk_obj.save()  # Save the updated object back to MongoDB

            updated_count += 1
            print(f"Updated embedding for chunk_id: {chunk_obj.chunk_id}, _id: {chunk_obj.pk}")  # chunk_obj.pk for MongoDB _id

        except Exception as e:
            error_count += 1
            print(f"Error embedding chunk_id: {chunk_obj.chunk_id}, _id: {chunk_obj.pk}: {e}")

    message = f"Embedding process completed. Updated {updated_count} chunks. Encountered {error_count} errors."
    print(message)
    return render(request, 'data_processing/embedding_process.html', {'message': message}) # You might need to create embedding_status.html
