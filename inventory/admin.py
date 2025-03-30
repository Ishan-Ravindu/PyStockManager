from django.contrib import admin
from .models import (
    Shop, Supplier, Customer, Product, Stock, 
    PurchaseInvoice, PurchaseInvoiceItem, 
    StockTransfer, StockTransferItem, 
    SalesInvoice, SalesInvoiceItem
)

class PurchaseInvoiceItemInline(admin.TabularInline):
    model = PurchaseInvoiceItem
    extra = 1

class SalesInvoiceItemInline(admin.TabularInline):
    model = SalesInvoiceItem
    extra = 1

class StockTransferItemInline(admin.TabularInline):
    model = StockTransferItem
    extra = 1

@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'is_warehouse')
    list_filter = ('is_warehouse',)
    search_fields = ('name', 'location')

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_info')
    search_fields = ('name', 'contact_info')

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_info', 'credit_limit', 'credit_period')
    list_filter = ('credit_period',)
    search_fields = ('name', 'contact_info')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'profit_margin', 'average_cost', 'selling_price')
    search_fields = ('name', 'description')
    list_filter = ('profit_margin',)

    def average_cost(self, obj):
        return obj.get_average_cost()
    
    def selling_price(self, obj):
        return obj.get_selling_price()

    average_cost.short_description = "Avg Cost"
    selling_price.short_description = "Selling Price"

@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('shop', 'product', 'quantity')
    list_filter = ('shop', 'product')
    search_fields = ('shop__name', 'product__name')

    def get_readonly_fields(self, request, obj=None):
        return ('quantity',)

    def has_add_permission(self, request):
        return False

@admin.register(PurchaseInvoice)
class PurchaseInvoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'supplier', 'shop', 'total_amount', 'created_at')
    list_filter = ('supplier', 'shop', 'created_at')
    search_fields = ('supplier__name', 'shop__name')
    readonly_fields = ('total_amount', 'created_at')
    inlines = [PurchaseInvoiceItemInline]

@admin.register(StockTransfer)
class StockTransferAdmin(admin.ModelAdmin):
    list_display = ('id', 'from_shop', 'to_shop', 'created_at')
    list_filter = ('from_shop', 'to_shop', 'created_at')
    search_fields = ('from_shop__name', 'to_shop__name')
    readonly_fields = ('created_at',)
    inlines = [StockTransferItemInline]

@admin.register(SalesInvoice)
class SalesInvoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'shop', 'customer', 'total_amount', 'created_at')
    list_filter = ('shop', 'customer', 'created_at')
    search_fields = ('shop__name', 'customer__name')
    readonly_fields = ('total_amount', 'created_at')
    inlines = [SalesInvoiceItemInline]