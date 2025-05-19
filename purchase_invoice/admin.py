from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin
from unfold.admin import TabularInline
from guardian.shortcuts import get_objects_for_user

from purchase_invoice.models import PurchaseInvoice, PurchaseInvoiceItem
from shop.models import Shop
from utils import invoice_number

class PurchaseInvoiceItemInline(TabularInline):
    model = PurchaseInvoiceItem
    autocomplete_fields = ['product']
    extra = 5

@admin.register(PurchaseInvoice)
class PurchaseInvoiceAdmin(SimpleHistoryAdmin, ModelAdmin):
    list_display = ('shop_code_and_id', 'supplier', 'shop', 'total_amount', 'paid_amount', 'created_at')
    list_filter = ('supplier', 'shop', 'created_at')
    search_fields = ('supplier__name', 'shop__name')
    readonly_fields = ('total_amount', 'paid_amount', 'created_at')
    inlines = [PurchaseInvoiceItemInline]
    autocomplete_fields = ['supplier']
    list_per_page = 20
    actions = None

    def shop_code_and_id(self, obj):
        return  invoice_number(obj.shop.code, obj.id)
    shop_code_and_id.short_description = 'Invoice ID'
    shop_code_and_id.admin_order_field = 'id'
    # if this need to change must be handle signal properly for shop change and supplier change
    def get_readonly_fields(self, request, obj=None):
        if obj:
            return  ('supplier', 'shop',) + self.readonly_fields 
        return self.readonly_fields
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        allowed_shops = get_objects_for_user(request.user, 'shop.view_shop', Shop)
        return qs.filter(shop__in=allowed_shops)
