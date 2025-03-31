from django.contrib import admin
from ..models import Shop, Supplier, Customer, Product

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
    list_display = ('name', 'contact_info', 'credit', 'credit_limit', 'credit_period')
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