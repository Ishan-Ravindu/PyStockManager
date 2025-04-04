from django.contrib import admin

from entity.models import Customer, Product, Shop, Supplier

@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'location', 'is_warehouse')
    list_filter = ('is_warehouse',)
    search_fields = ('name', 'location')
    list_per_page = 20

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'mobile_number')
    search_fields = ('name', 'mobile_number')
    list_per_page = 20

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'mobile_number', 'address', 'credit', 'credit_limit', 'credit_period', 'combined_status', 'black_list')
    list_filter = ('credit_period',)
    search_fields = ('name', 'mobile_number')
    readonly_fields = ('credit',)
    list_per_page = 20

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'profit_margin')
    search_fields = ('name', 'description')
    list_filter = ('profit_margin',)
    list_per_page = 20
