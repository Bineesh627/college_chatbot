from django.shortcuts import render
from .models import CrawledURL, DocumentChunks
from langchain_community.document_loaders import WebBaseLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_community.docstore.document import Document
import json  # Import json module
import re

def data_source(request):
    return render(request, 'data_processing/data_source.html')

# Clean Text
def clean_text(text):
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\[email\xa0protected\]', 'email-hidden', text)
    text = re.sub(r'Toggle navigation', '', text)
    return text.strip()

def start_content():

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
            # Load document for a single URL
            loader = WebBaseLoader([url])
            docs = loader.load()

            if not docs:
                print(f"No documents loaded for URL: {url}")
                continue  # Skip to the next URL if no documents are loaded

            # Split the document into chunks
            chunks = text_splitter.split_documents(docs)

            # Get the CrawledURL instance for this URL to link chunks
            crawled_url_instance = CrawledURL.objects.get(source_url=url)

            for chunk in chunks:
                cleaned_content = clean_text(chunk.page_content)

                # Use update_or_create to prevent duplicates
                DocumentChunks.objects.update_or_create(
                    crawled_url=crawled_url_instance,
                    content=cleaned_content,
                    defaults={'embedding': {}}  # Embeddings will be added later
                )
            print(f"Processed and stored chunks for URL: {url}")

        except CrawledURL.DoesNotExist:
            print(f"CrawledURL instance not found for URL: {url}")
        except Exception as e:
            print(f"Error processing URL {url}: {e}")

    return render(request, 'data_processing/content_process.html', {'message': message})

def get_embedding_function():
    # Initialize Embeddings (ensure Ollama is running at http://localhost:11434)
    embedding_model = OllamaEmbeddings(model="llama3.2", base_url="http://localhost:11434")
    return get_embedding_function

# Define a function that takes a text input and returns the embedding vector
    # def embedding_function(text):
    #     # Generate embedding for the content
    #     embedding_vector = embedding_model.embed_query(text)
    #     return embedding_vector

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
