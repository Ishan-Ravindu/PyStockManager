from django.contrib import admin

from inventory.models.sales import Receipt
from ..models import SalesInvoice, SalesInvoiceItem

class SalesInvoiceItemInline(admin.TabularInline):
    model = SalesInvoiceItem
    extra = 1

@admin.register(SalesInvoice)
class SalesInvoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'shop', 'customer', 'total_amount', 'paid_amount', 'created_at')
    list_filter = ('shop', 'customer', 'created_at')
    search_fields = ('shop__name', 'customer__name')
    readonly_fields = ('total_amount', 'created_at')
    inlines = [SalesInvoiceItemInline]

@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ('id', 'sales_invoice', 'amount', 'payment_method', 'received_at')
