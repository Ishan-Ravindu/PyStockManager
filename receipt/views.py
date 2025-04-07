from django.shortcuts import get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse

from utils import render_to_pdf
from .models import Receipt
from django.utils import timezone

@staff_member_required
def generate_receipt_pdf(request, receipt_id):
    """Generate PDF for a receipt"""
    receipt = get_object_or_404(Receipt, id=receipt_id)
    
    context = {
        'receipt': receipt,
        'invoice': receipt.sales_invoice,
        'today': timezone.now(),
        'company_name': 'Your Company Name',
        'company_address': 'Your Company Address',
        'company_phone': '0123456789',
        'company_email': 'info@yourcompany.com',
    }
    
    pdf = render_to_pdf('sales/receipt_pdf.html', context)
    
    if pdf:
        response = HttpResponse(pdf, content_type='application/pdf')
        filename = f"Receipt_{receipt.id}.pdf"
        content = f"attachment; filename={filename}"
        response['Content-Disposition'] = content
        return response
    
    return HttpResponse("Error generating PDF", status=400)