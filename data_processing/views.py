from django.shortcuts import render
from .models import CrawledURL, DocumentChunks, UploadedDocument
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_community.docstore.document import Document
from langchain_aws import BedrockEmbeddings
import requests
from langchain_community.document_loaders import PyPDFLoader
from bs4 import BeautifulSoup
import json  # Import json module
import re
import requests
import os
import urllib.parse
import uuid
from django.conf import settings
from django.http import HttpResponse
import hashlib

def data_source(request):
    return render(request, 'data_processing/data_source.html')

def decode_email(encoded_email):
    decoded = ''
    hex_value = int(encoded_email[:2], 16)
    for i in range(2, len(encoded_email), 2):
        decoded += chr(int(encoded_email[i:i+2], 16) ^ hex_value)
    return decoded

def clean(text):
    text = text.replace("\n", " ")
    text = text.replace("\t", " ")
    text = re.sub(r'&nbsp;?', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    text = text.lower()
    return text

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
        cleaned_text = clean(body_content)

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
        return [Document(page_content=cleaned_text, metadata={"source": url})]  # Correct return type


    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

def split_documents(documents):
    # Use the RecursiveCharacterTextSplitter to split the document into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800, # Set the chunk size
        chunk_overlap=80, # Set the overlap between chunks
        length_function=len, # Use len() as the length function
        is_separator_regex=False, # Set to True if you have a separator regex
    )
    # Split the documents into chunks
    return text_splitter.split_documents(documents)

def start_content(request):
    message = "" # Define message variable

    # Load URLs with status_code 200 directly and convert to Python list
    urls_queryset = CrawledURL.objects.filter(status_code=200).values_list('source_url', flat=True)
    urls = list(urls_queryset)

    for url in urls:
        try:
            # Load document for a single URL using your custom function
            extracted_document_list = clean_and_extract_data(url) # Renamed docs to extracted_document_list

            if not extracted_document_list: # Check for empty list (or None)
                print(f"No documents loaded for URL: {url}")
                message += f"No documents loaded for URL: {url}<br>"
                continue  # Skip to the next URL if no documents are loaded

            # Split the document into chunks - now using correct input type
            chunks = split_documents(extracted_document_list)
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

def generate_embeddings(text_to_embedding):
    """Generate embeddings for the given text."""
    embeddings = get_embedding_function()  # Get the embedding function
    embedding_vector = embeddings.embed_query(text_to_embedding)  # Generate the embedding vector
    return embedding_vector  # Return the generated embedding vector

def start_embedding(request):
    # Fetch all DocumentChunks records from MongoDB
    document_chunks = DocumentChunks.objects.all()

    updated_count = 0
    error_count = 0

    for chunk_obj in document_chunks:  # Iterate through DocumentChunks objects directly
        try:
            content_to_embed = chunk_obj.content
            print(content_to_embed)

            # Generate embedding for the content
            embedding_vector = generate_embeddings(content_to_embed)
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

def process_url(url):
    """Fetch all PDF links from the specified URL."""
    try:
        # Send a GET request to the URL
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad responses
        soup = BeautifulSoup(response.content, 'html.parser')  # Parse the HTML content

        pdf_data = []  # Initialize an empty list to store PDF data

        links = soup.find_all('a', href=True)  # Find all anchor tags with href attributes
        for link in links:
            href = link['href']  # Get the href attribute of the link
            if href.endswith('.pdf'):  # Check if the link ends with .pdf
                title = link.get('title')  # Get the title attribute of the link
                if title:
                    text = title.strip()  # Use the title if available
                else:
                    # Fallback to extracting text from nested elements
                    text = link.find('p').find('b').text.strip() if link.find('p') and link.find('p').find('b') else link.get_text().strip()

                pdf_data.append((text, href))  # Append the text and href to the pdf_data list

        return pdf_data  # Return the list of PDF data


    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL: {e}")  # Log any request errors
        return None  # Return None on error
    except Exception as e:
        print(f"An unexpected error occurred: {e}")  # Log any unexpected errors
        return None  # Return None on error


def download_pdf(url):
    """Download a PDF from the specified URL and save it to the local filesystem."""
    try:
        # Send a GET request to the URL to download the PDF
        response = requests.get(url, stream=True)
        response.raise_for_status()  # Raise an error for bad responses

        pdf_content = b''  # Initialize a byte string to hold the PDF content
        for chunk in response.iter_content(chunk_size=8192):  # Read the content in chunks
            pdf_content += chunk  # Append each chunk to the pdf_content

        # Calculate the SHA256 hash of the PDF content
        pdf_hash = hashlib.sha256(pdf_content).hexdigest()

        # Generate a random filename for the PDF
        random_filename = f"{uuid.uuid4()}.pdf"
        downloads_dir = os.path.join(settings.MEDIA_ROOT, "documents")  # Define the download directory
        os.makedirs(downloads_dir, exist_ok=True)  # Create the directory if it doesn't exist
        filepath = os.path.join(downloads_dir, random_filename)  # Define the full file path

        # Write the PDF content to a file
        with open(filepath, 'wb') as pdf_file:
            pdf_file.write(pdf_content)  # Save the content to the file

        return filepath, random_filename, pdf_hash  # Return the file path, filename, and hash

    except requests.exceptions.RequestException as e:
        print(f"Error downloading PDF: {e}")  # Log any request errors
        return None, None, None  # Return None values on error
    except OSError as e:
        print(f"Error saving PDF: {e}")  # Log any file system errors
        return None, None, None  # Return None values on error

def process_pdfs(file_path):
    """Load and process PDFs from the specified file path."""
    document_loader = PyPDFLoader(file_path)  # Create a PDF loader instance
    documents = document_loader.load()  # Load the documents from the PDF
    return documents

def pdf_process(request):
    # Check if the request method is POST
    if request.method == 'POST':
        # Get the PDF URL from the POST request
        pdf_url = request.POST.get('pdf_url')

        # Process the URL to fetch PDF links
        pdf_list = process_url(pdf_url)
        if pdf_list:
            # Iterate through each PDF link found
            for text, url in pdf_list:
                # Check if the document already exists in the database
                if UploadedDocument.objects.filter(document_url=url).exists():
                    print(f"Document with URL '{url}' already exists. Skipping download.")
                    continue
                
                # Download the PDF file
                filepath, filename, pdf_hash = download_pdf(url)
                if filepath:
                    # Check if a document with the same content already exists
                    if UploadedDocument.objects.filter(pdf_hash=pdf_hash).exists():
                        print(f"Document with identical content already exists. Skipping database save.")
                        os.remove(filepath)  # Remove the downloaded file
                        continue

                    try:
                        # Create a new UploadedDocument instance
                        document = UploadedDocument(
                            document_title=text,
                            document_url=url,
                            file_path=os.path.join("documents", filename),
                            file_type="PDF",
                            pdf_hash=pdf_hash,
                        )
                        document.save()  # Save the document to the database
                        print(f"Document saved to database: {document.document_id}")

                        # Process the PDF and create chunks
                        documents = process_pdfs(filepath)
                        chunks = split_documents(documents)

                        # Iterate through each chunk created from the PDF
                        for chunk in chunks:
                            cleaned_content = clean(chunk.page_content)  # Clean the chunk content
                            # Generate embeddings for the cleaned content
                            embedding_vector = generate_embeddings(cleaned_content)

                            # Create a DocumentChunks instance for each chunk
                            DocumentChunks.objects.create(
                                document=document,
                                content=cleaned_content,
                                embedding=embedding_vector,
                            )
                            print(f"Chunk created for document {document.document_id}")

                    except Exception as db_error:
                        print(f"Error saving to database: {db_error}")
                        return HttpResponse(f"Database error: {db_error}")

                # Log the details of the processed PDF
                print(f"Text: {text}")
                print(f"URL: {url}")
                print(f"file path: {filepath}")
                print(f"file is a: pdf")
            return HttpResponse("PDFs processed and saved successfully.")
        else:
            return HttpResponse("No PDFs found or error processing URL.")
    return render(request, 'data_processing/pdf_process.html')
