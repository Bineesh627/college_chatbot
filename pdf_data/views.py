from django.shortcuts import render
from django.core.paginator import Paginator
from .models import UploadedDocument, DocumentChunks

import os
import re
import uuid
import hashlib
from django.conf import settings
from django.http import HttpResponse
from django.core.files.storage import default_storage
from model_api.views import generate_embeddings, chunk_content
from langchain_community.document_loaders import PyPDFLoader

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

def manage_uploaded_pdfs(request):
    """Handle both PDF uploads and document listing with pagination."""
    
    if request.method == "POST" and request.FILES.get("pdfFile"):
        try:
            pdf_file = request.FILES["pdfFile"]

            # Read PDF content
            pdf_content = pdf_file.read()

            # Compute SHA256 hash
            pdf_hash = hashlib.sha256(pdf_content).hexdigest()

            # Check if a duplicate document exists
            if UploadedDocument.objects.filter(pdf_hash=pdf_hash).exists():
                print("Document with identical content already exists. Skipping database save.")
                return HttpResponse("Duplicate file detected. File not saved.", status=400)

            # Generate filename & save PDF
            random_filename = f"{uuid.uuid4()}.pdf"
            downloads_dir = os.path.join(settings.MEDIA_ROOT, "documents")
            os.makedirs(downloads_dir, exist_ok=True)
            filepath = os.path.join(downloads_dir, random_filename)

            with open(filepath, 'wb') as output_file:
                output_file.write(pdf_content)

            # Save document to database
            document = UploadedDocument(
                document_title=pdf_file.name,
                document_url=None,  # Store file URL
                file_path=f"documents/{random_filename}",
                file_type="PDF",
                pdf_hash=pdf_hash,
            )
            document.save()
            print(f"Document saved to database: {document.document_id}")

            # Process and chunk the PDF
            documents = process_pdfs(filepath) or []  # Ensure a list is returned
            if not documents:
                return HttpResponse("Failed to process PDF content.", status=400)

            merged_content = " ".join([doc.page_content for doc in documents])
            chunks = chunk_content(merged_content) if merged_content else []

            # Save chunks with embeddings
            for chunk in chunks:
                cleaned_content = clean(chunk) or ""  # Ensure it's not None
                if not cleaned_content:
                    continue  # Skip empty chunks

                try:
                    embedding_vector = generate_embeddings(cleaned_content)
                except Exception as e:
                    print(f"Error generating embedding: {e}")
                    embedding_vector = None

                DocumentChunks.objects.create(
                    document=document,
                    content=cleaned_content,
                    embedding=embedding_vector,
                )
                print(f"Chunk created for document {document.document_id}")

        except OSError as e:
            print(f"Error saving PDF: {e}")
            return HttpResponse(f"File system error: {e}", status=500)

    # Retrieve document list with pagination
    documents_list = UploadedDocument.objects.all().order_by('-created_at')

    # Get pagination settings
    rows_per_page = request.GET.get('rows', 25)
    if str(rows_per_page) not in ["25", "50"]:
        rows_per_page = 25

    paginator = Paginator(documents_list, int(rows_per_page))
    page_number = request.GET.get('page')
    
    try:
        documents = paginator.get_page(page_number)
    except:
        documents = paginator.get_page(1)  # Default to first page if invalid

    return render(request, 'pdf_data/pdf_process.html', {
        'documents': documents,
        'rows_per_page': rows_per_page,
        'media_url': settings.MEDIA_URL
    })
