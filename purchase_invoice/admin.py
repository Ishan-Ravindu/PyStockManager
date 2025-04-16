from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin
from unfold.admin import TabularInline

from purchase_invoice.models import PurchaseInvoice, PurchaseInvoiceItem

class PurchaseInvoiceItemInline(TabularInline):
    model = PurchaseInvoiceItem
    extra = 0

@admin.register(PurchaseInvoice)
class PurchaseInvoiceAdmin(SimpleHistoryAdmin, ModelAdmin):
    list_display = ('id', 'supplier', 'shop', 'total_amount', 'paid_amount', 'created_at')
    list_filter = ('supplier', 'shop', 'created_at')
    search_fields = ('supplier__name', 'shop__name')
    readonly_fields = ('total_amount', 'paid_amount', 'created_at')
    inlines = [PurchaseInvoiceItemInline]
    list_per_page = 20

    # save_as = False
    # save_on_top = False
    # def has_change_permission(self, request, obj=None):
    #     return False 
    # def has_delete_permission(self, request, obj=None):
    #     return False