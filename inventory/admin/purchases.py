from django.contrib import admin
from ..models import PurchaseInvoice, PurchaseInvoiceItem

class PurchaseInvoiceItemInline(admin.TabularInline):
    model = PurchaseInvoiceItem
    extra = 1

@admin.register(PurchaseInvoice)
class PurchaseInvoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'supplier', 'shop', 'total_amount', 'created_at')
    list_filter = ('supplier', 'shop', 'created_at')
    search_fields = ('supplier__name', 'shop__name')
    readonly_fields = ('total_amount', 'created_at')
    inlines = [PurchaseInvoiceItemInline]

    save_as = False
    save_on_top = False
    def has_change_permission(self, request, obj=None):
        return False 
    def has_delete_permission(self, request, obj=None):
        return False