from django.contrib import admin
from django.core.exceptions import ValidationError
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.shortcuts import redirect

from sale_invoice.models import SalesInvoice, SalesInvoiceItem
from utils import invoice_number
from .forms import SalesInvoiceForm
from .inlines import SalesInvoiceItemInline
from .mixins import PDFViewMixin, MessageMixin
from .services import InvoiceService
from .validators import InvoiceValidator

@admin.register(SalesInvoice)
class SalesInvoiceAdmin(SimpleHistoryAdmin, PDFViewMixin, MessageMixin, ModelAdmin):
    """Admin interface for sales invoices"""
    form = SalesInvoiceForm
    list_display = ('shop_code_and_id', 'customer', 'total_amount', 'paid_amount', 'created_at', 
                   'due_date', 'payment_status', 'add_receipt_button', 'view_receipts', 
                   'view_invoice_pdf')
    list_filter = ('shop', 'customer', 'created_at')
    search_fields = ('shop__name', 'customer__name')
    readonly_fields = ('total_amount', 'paid_amount', 'created_at')
    exclude = ('created_at',)
    inlines = [SalesInvoiceItemInline]
    list_per_page = 20
    actions = None

    class Media:
        js = ('sale_invoice/js/sales_invoice_customer.js','sale_invoice/js/sales_invoice_items.js',)

    def shop_code_and_id(self, obj):
        return  invoice_number(obj.shop.code, obj.id)
    shop_code_and_id.short_description = 'Invoice ID'
    shop_code_and_id.admin_order_field = 'id'
    
    def has_delete_permission(self, request, obj=None):
        if not InvoiceService.can_delete_invoice(obj):
            return False
        return super().has_delete_permission(request, obj)
   
    def save_model(self, request, obj, form, change):
        if change:
            try:
                InvoiceValidator.validate_can_edit(obj)
            except ValidationError as e:
                self.display_error(request, str(e))
                return
        
        super().save_model(request, obj, form, change)
    
    def save_related(self, request, form, formsets, change):
        items_count = 0
        for formset in formsets:
            if formset.model == SalesInvoiceItem:
                for item_form in formset.forms:
                    if (item_form.is_valid() and 
                        not item_form.cleaned_data.get('DELETE', False) and
                        item_form.cleaned_data.get('product') and 
                        item_form.cleaned_data.get('quantity')):
                        items_count += 1
        try:
            InvoiceValidator.validate_has_items(items_count)
        except ValidationError as e:
            self.display_error(request, str(e))
            return
            
        super().save_related(request, form, formsets, change)
    
    def response_change(self, request, obj):
        if not InvoiceService.can_edit_invoice(obj):
            return redirect(reverse('admin:inventory_salesinvoice_changelist'))
        return super().response_change(request, obj)

    def delete_model(self, request, obj):
        if not InvoiceService.can_delete_invoice(obj):
            receipt_list = InvoiceService.get_receipt_list_display(obj)
            self.display_error(
                request,
                f"Cannot delete Invoice #{obj.id} ({obj.shop.code}) because it has "
                f"linked receipts: {receipt_list}"
            )
            return
        
        invoice_ref = f"Invoice #{obj.id} ({obj.shop.code})"
        obj.delete()
        self.display_success(request, f"{invoice_ref} was deleted successfully")

    def response_delete(self, request, obj_display, obj_id):
        return redirect(reverse('admin:sale_invoice_salesinvoice_changelist'))

    def add_receipt_button(self, obj):
        url = reverse('admin:receipt_receipt_add') + f'?invoice={obj.id}'
        return format_html('<a class="button" href="{}">Add Receipt</a>', url)
    add_receipt_button.short_description = 'Add Receipt'

    def view_receipts(self, obj):
        receipts = obj.receipts.all()
        if not receipts:
            return "No receipts"        
        
        links = []
        for receipt in receipts:
            url = reverse('admin:receipt_receipt_change', args=[receipt.id])
            links.append(f'<a href="{url}">{receipt.id}({receipt.amount})</a>')        
        
        return mark_safe(', '.join(links))
    view_receipts.short_description = 'Receipts history'

    def view_invoice_pdf(self, obj):
        return self.get_pdf_button(obj, 'generate_invoice_pdf')
    view_invoice_pdf.short_description = 'Invoice PDF'
