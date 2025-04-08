from django.shortcuts import get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse

from utils import render_to_pdf
from .models import SalesInvoice
from django.utils import timezone

@staff_member_required
def generate_invoice_pdf(request, invoice_id):
    """Generate PDF for a sales invoice"""
    invoice = get_object_or_404(SalesInvoice, id=invoice_id)
    items = invoice.items.all()
    
    # Calculate total quantity and subtotals for each item
    for item in items:
        item.subtotal = item.price * item.quantity
    
    context = {
        'invoice': invoice,
        'items': items,
        'today': timezone.now(),
        'company_name': 'Your Company Name',
        'company_address': 'Your Company Address',
        'company_phone': '0123456789',
        'company_email': 'info@yourcompany.com',
    }
    
    pdf = render_to_pdf('sales/invoice_pdf.html', context)
    
    if pdf:
        response = HttpResponse(pdf, content_type='application/pdf')
        filename = f"Invoice_{invoice.id}.pdf"
        content = f"attachment; filename={filename}"
        response['Content-Disposition'] = content
        return response
    
    return HttpResponse("Error generating PDF", status=400)
