import os
import requests
import hashlib
import uuid
import re
from django.conf import settings
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from .models import DocumentChunks, UploadedDocument
from model_api.views import generate_embeddings


def download_pdf(url):
    """Download a PDF from the specified URL and save it locally."""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()

        pdf_content = response.content  # Get the binary content

        # Generate SHA256 hash
        pdf_hash = hashlib.sha256(pdf_content).hexdigest()

        # Generate a random filename
        random_filename = f"{uuid.uuid4()}.pdf"
        downloads_dir = os.path.join(settings.MEDIA_ROOT, "documents")
        os.makedirs(downloads_dir, exist_ok=True)

        filepath = os.path.join(downloads_dir, random_filename)

        with open(filepath, 'wb') as pdf_file:
            pdf_file.write(pdf_content)

        return filepath, random_filename, pdf_hash
    except requests.exceptions.RequestException as e:
        print(f"Error downloading PDF: {e}")
        return None, None, None


def process_pdfs(file_path):
    """Load and process PDFs from the specified file path."""
    document_loader = PyPDFLoader(file_path)
    documents = document_loader.load()
    return documents


def clean(text):
    """Clean text by removing symbols and normalizing whitespace."""
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r'\s+', ' ', text.replace("\n", " ").replace("\t", " ")).strip().lower()
    return text


def chunk_content(text):
    """Split text into manageable chunks."""
    return RecursiveCharacterTextSplitter(
        chunk_size=800, chunk_overlap=80, length_function=len, is_separator_regex=False
    ).split_text(text)

def pdf_process():
    """Process PDFs from uploaded URLs without requiring a request."""
    pdf_urls = UploadedDocument.objects.values_list('document_url', flat=True)

    if not pdf_urls:
        print("No PDFs found or error processing URL.")
        return

    for url in pdf_urls:
        filepath, filename, pdf_hash = download_pdf(url)
        if not filepath:
            continue

        if UploadedDocument.objects.filter(pdf_hash=pdf_hash).exists():
            print("Duplicate document found. Skipping.")
            os.remove(filepath)
            continue

        try:
            document = UploadedDocument.objects.create(
                file_path=os.path.join("documents", filename),
                pdf_hash=pdf_hash,
                document_url=url
            )
            print(f"Document saved: {document.document_id}")

            documents = process_pdfs(filepath)
            text = " ".join([doc.page_content for doc in documents])
            chunks = chunk_content(text)

            for chunk in chunks:
                cleaned_content = clean(chunk)
                embedding_vector = generate_embeddings(cleaned_content)
                DocumentChunks.objects.create(
                    document=document,
                    content=cleaned_content,
                    embedding=embedding_vector,
                )

            print(f"Chunks created for {document.document_id}")

        except Exception as e:
            print(f"Database error: {e}")

    print("Processing completed.")

