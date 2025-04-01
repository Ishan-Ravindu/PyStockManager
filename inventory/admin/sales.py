from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from inventory.models.sales import Receipt
from ..models import SalesInvoice, SalesInvoiceItem

class SalesInvoiceItemInline(admin.TabularInline):
    model = SalesInvoiceItem
    extra = 1

@admin.register(SalesInvoice)
class SalesInvoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'shop', 'customer', 'total_amount', 'paid_amount', 'created_at', 'due_date', 'payment_status', 'add_receipt_button', 'view_receipts')
    list_filter = ('shop', 'customer', 'created_at')
    search_fields = ('shop__name', 'customer__name')
    readonly_fields = ('total_amount', 'created_at')
    inlines = [SalesInvoiceItemInline]

    def payment_status(self, obj):
        from django.utils import timezone
        
        if obj.total_amount <= obj.paid_amount:
            return format_html('<span style="color: green; font-weight: bold;">Paid</span>')
        elif obj.due_date and obj.due_date < timezone.now().date():
            return format_html('<span style="color: red; font-weight: bold;">Overdue</span>')
        elif obj.paid_amount == 0:
            return format_html('<span style="color: orange; font-weight: bold;">Unpaid</span>')
        else:
            return format_html('<span style="color: blue; font-weight: bold;">Partially Paid</span>')
    payment_status.short_description = 'Status'

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
    view_receipts.short_description = 'Receipts'

@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ('id', 'sales_invoice', 'amount', 'payment_method', 'received_at',)
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj is None and 'invoice' in request.GET:
            try:
                invoice_id = int(request.GET.get('invoice'))
                form.base_fields['sales_invoice'].initial = invoice_id
            except (ValueError, TypeError):
                pass
        return form
