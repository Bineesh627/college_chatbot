from django.shortcuts import render
from bs4 import BeautifulSoup
import requests
import os
import re
from django.http import HttpResponse
import json  # Import json module
import hashlib
import urllib.parse
import uuid
from django.conf import settings
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from .models import DocumentChunks, UploadedDocument
from model_api.views import generate_embeddings, chunk_content
from admin_panel.decorators import admin_required

# Create your views here.

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

def clean(text):
    symbol_pattern = r"[^\w\s]"
    text = re.sub(symbol_pattern, " ", text)
    text = re.sub(r'\s+', ' ', text.replace("\n", " ").replace("\t", " ")).strip().lower()
    return text

@admin_required
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
                        chunks = chunk_content(" ".join([doc.page_content for doc in documents]))
                        # chunks = chunk_content(documents)

                        # Iterate through each chunk created from the PDF
                        for chunk in chunks:
                            cleaned_content = clean(chunk) # Clean the chunk content
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
    return render(request, 'pdf_data/pdf_process.html')
