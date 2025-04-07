from django import forms
from django.contrib import admin, messages
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.shortcuts import redirect
from django.forms import ValidationError

from inventory.models.sales import Receipt
from ..models import SalesInvoice, SalesInvoiceItem

class SalesInvoiceItemInline(admin.StackedInline):
    model = SalesInvoiceItem
    extra = 1
        
class ReceiptInline(admin.StackedInline):
    model = Receipt
    extra = 1
    readonly_fields = ('view_receipt_pdf',)
    
    def view_receipt_pdf(self, obj):
        if obj.id:
            url = reverse('generate_receipt_pdf', args=[obj.id])
            return format_html('<a class="button" href="{}" target="_blank"><i class="fa fa-file-pdf"></i> View PDF</a>', url)
        return "-"
    view_receipt_pdf.short_description = 'Receipt PDF'
    
    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        
        # Validate receipt amount doesn't exceed the remaining unpaid amount
        original_clean = formset.form.clean
        
        def clean_receipt_form(form_instance):
            cleaned_data = original_clean(form_instance)
            
            # Skip validation if the form is empty or marked for deletion
            if not cleaned_data or form_instance.cleaned_data.get('DELETE', False):
                return cleaned_data
                
            amount = cleaned_data.get('amount')
            receipt_id = form_instance.instance.pk
            sales_invoice = obj
            
            if amount is not None and sales_invoice:
                remaining_amount = sales_invoice.total_amount - sales_invoice.paid_amount
                
                # If editing an existing receipt, add back the original amount
                if receipt_id:
                    original_receipt = Receipt.objects.get(pk=receipt_id)
                    remaining_amount += original_receipt.amount
                    
                if amount > remaining_amount:
                    raise ValidationError({
                        'amount': f'Receipt amount cannot exceed the remaining unpaid amount of {remaining_amount}.'
                    })
                    
            return cleaned_data
            
        formset.form.clean = clean_receipt_form
        return formset

@admin.register(SalesInvoice)
class SalesInvoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'shop', 'customer', 'total_amount', 'paid_amount', 'created_at', 'due_date', 'payment_status', 'add_receipt_button', 'view_receipts', 'view_invoice_pdf')
    list_filter = ('shop', 'customer', 'created_at')
    search_fields = ('shop__name', 'customer__name')
    readonly_fields = ('total_amount', 'created_at')
    exclude = ('created_at',)
    inlines = [SalesInvoiceItemInline, ReceiptInline]
    list_per_page = 20
    actions = None
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        
        # Add form validation for blacklisted customers
        original_clean = form.clean
        
        def clean_with_blacklist_check(form_instance):
            cleaned_data = original_clean(form_instance)
            customer = cleaned_data.get('customer')
            
            if customer and customer.black_list:
                raise ValidationError("Cannot create an invoice for a blacklisted customer.")
                
            return cleaned_data
            
        form.clean = clean_with_blacklist_check
        return form
    
    def has_delete_permission(self, request, obj=None):
        # Override to check if the object can be deleted
        if obj and obj.receipts.exists():
            return False
        return super().has_delete_permission(request, obj)
   
    def save_model(self, request, obj, form, change):
        # Check if invoice has receipts before allowing edit
        if change and obj.receipts.exists():
            receipt_list = ", ".join([str(receipt.id) for receipt in obj.receipts.all()[:5]])
            if obj.receipts.count() > 5:
                receipt_list += f" (and {obj.receipts.count() - 5} more)"
                
            messages.error(
                request,
                f"Cannot edit Invoice #{obj.id} ({obj.shop.code}) because it has "
                f"linked receipts: {receipt_list}"
            )
            return
        super().save_model(request, obj, form, change)
    
    def response_change(self, request, obj):
        if obj.receipts.exists():
            return redirect(reverse('admin:inventory_salesinvoice_changelist'))
        return super().response_change(request, obj)

    def delete_model(self, request, obj):
        if obj.receipts.exists():
            receipt_list = ", ".join([str(receipt.id) for receipt in obj.receipts.all()[:5]])
            if obj.receipts.count() > 5:
                receipt_list += f" (and {obj.receipts.count() - 5} more)"
                
            messages.error(
                request,
                f"Cannot delete Invoice #{obj.id} ({obj.shop.code}) because it has "
                f"linked receipts: {receipt_list}"
            )
            return
        else:
            invoice_ref = f"Invoice #{obj.id} ({obj.shop.code})"
            obj.delete()
            messages.success(
                request, 
                f"{invoice_ref} was deleted successfully"
            )

    def response_delete(self, request, obj_display, obj_id):
        return redirect(reverse('admin:inventory_salesinvoice_changelist'))

    def add_receipt_button(self, obj):
        url = reverse('admin:inventory_receipt_add') + f'?invoice={obj.id}'
        return format_html('<a class="button" href="{}">Add Receipt</a>', url)
    add_receipt_button.short_description = 'Add Receipt'

    def view_receipts(self, obj):
        receipts = obj.receipts.all()
        if not receipts:
            return "No receipts"        
        links = []
        for receipt in receipts:
            url = reverse('admin:inventory_receipt_change', args=[receipt.id])
            links.append(f'<a href="{url}">{receipt.id}({receipt.amount})</a>')        
        return mark_safe(', '.join(links))
    view_receipts.short_description = 'Receipts history'

    def view_invoice_pdf(self, obj):
        if obj.id:
            url = reverse('generate_invoice_pdf', args=[obj.id])
            return format_html('<a class="button" href="{}" target="_blank"><i class="fa fa-file-pdf"></i> View PDF</a>', url)
        return "-"
    view_invoice_pdf.short_description = 'Invoice PDF'


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ('id', 'sales_invoice', 'amount', 'account', 'received_at', 'view_receipt_pdf')
    list_filter = ('account', 'received_at')
    search_fields = ('sales_invoice__customer__name',)
    list_per_page = 20
    
    def get_form(self, request, obj=None, **kwargs):
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
        
        # Add validation for receipt amount
        original_clean = form.clean
        
        def clean_with_amount_validation(form_instance):
            cleaned_data = original_clean(form_instance)
            amount = cleaned_data.get('amount')
            sales_invoice = cleaned_data.get('sales_invoice')
            
            if amount is not None and sales_invoice:
                remaining_amount = sales_invoice.total_amount - sales_invoice.paid_amount
                
                # If editing an existing receipt, add back the original amount
                if obj:
                    remaining_amount += obj.amount
                    
                if amount > remaining_amount:
                    raise ValidationError({
                        'amount': f'Receipt amount cannot exceed the remaining unpaid amount of {remaining_amount}.'
                    })
                    
            return cleaned_data
            
        form.clean = clean_with_amount_validation
        return form
    
    def view_receipt_pdf(self, obj):
        if obj.id:
            url = reverse('generate_receipt_pdf', args=[obj.id])
            return format_html('<a class="button" href="{}" target="_blank"><i class="fa fa-file-pdf"></i> View PDF</a>', url)
        return "-"
    view_receipt_pdf.short_description = 'Receipt PDF'