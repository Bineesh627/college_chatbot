

from django.shortcuts import render
from django.core.paginator import Paginator
from .models import UploadedDocument

def pdf_process(request): 

    documents_list = UploadedDocument.objects.all().order_by('-created_at')

    rows_per_page = request.GET.get('rows', 25)
    if str(rows_per_page) not in ["25", "50"]:
        rows_per_page = 25

    paginator = Paginator(documents_list, int(rows_per_page))
    page_number = request.GET.get('page')
    documents = paginator.get_page(page_number)

    return render(request, 'pdf_data/pdf_process.html', {'documents': documents, 'rows_per_page': int(rows_per_page)})
