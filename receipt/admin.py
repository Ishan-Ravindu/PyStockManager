from django.contrib import admin
from django.forms import ModelForm, ValidationError
from django.urls import reverse
from django.utils.html import format_html

from receipt.models import Receipt

class PDFViewMixin:
    """Mixin for adding PDF view buttons to admin"""
    
    def get_pdf_button(self, obj, url_name, button_text="View PDF"):
        """Generate HTML for PDF view button"""
        if obj and obj.id:
            url = reverse(url_name, args=[obj.id])
            return format_html(
                '<a class="button" href="{}" target="_blank"><i class="fa fa-file-pdf"></i> {}</a>',
                url, button_text
            )
        return "-"

class ReceiptValidator:
    """Validator class for receipt-related validations"""
    
    @staticmethod
    def validate_amount(amount, sales_invoice, original_amount=0):
        """Validate that receipt amount doesn't exceed remaining unpaid amount"""
        if not all([amount is not None, sales_invoice]):
            return
            
        remaining_amount = sales_invoice.total_amount - sales_invoice.paid_amount + original_amount
                
        if amount > remaining_amount:
            raise ValidationError(
                f"Receipt amount cannot exceed the remaining unpaid amount of {remaining_amount}."
            )


class ReceiptForm(ModelForm):
    """Custom form for receipts with amount validation"""
    
    class Meta:
        model = Receipt
        fields = '__all__'
    
    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data.get('amount')
        sales_invoice = cleaned_data.get('sales_invoice')
        
        # Get original amount if editing existing receipt
        original_amount = 0
        if self.instance and self.instance.pk:
            original_amount = self.instance.amount
        
        # Validate receipt amount
        if amount is not None and sales_invoice:
            try:
                ReceiptValidator.validate_amount(amount, sales_invoice, original_amount)
            except ValidationError as e:
                self.add_error('amount', e)
        
        return cleaned_data


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin, PDFViewMixin):
    """Admin interface for receipts"""
    form = ReceiptForm
    list_display = ('id', 'sales_invoice', 'amount', 'account', 'received_at', 'view_receipt_pdf')
    list_filter = ('account', 'received_at')
    search_fields = ('sales_invoice__customer__name',)
    list_per_page = 20
    
    def get_form(self, request, obj=None, **kwargs):
        """Custom form handling for receipts"""
        form = super().get_form(request, obj, **kwargs)
        
        # Pre-load invoice when adding a new receipt
        if obj is None and 'invoice' in request.GET:
            try:
                invoice_id = int(request.GET.get('invoice'))
                form.base_fields['sales_invoice'].initial = invoice_id
            except (ValueError, TypeError):
                pass
                
        # Disable sales_invoice field when editing an existing receipt
        elif obj is not None:
            form.base_fields['sales_invoice'].disabled = True
            
        # Disable the + icon specifically for sales_invoice
        form.base_fields['sales_invoice'].widget.can_add_related = False
        
        return form
    
    def view_receipt_pdf(self, obj):
        """Generate PDF view button for receipt"""
        return self.get_pdf_button(obj, 'generate_receipt_pdf')
    view_receipt_pdf.short_description = 'Receipt PDF'
