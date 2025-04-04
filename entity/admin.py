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
    list_per_page = 20

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'profit_margin', 'average_cost', 'selling_price')
    search_fields = ('name', 'description')
    list_filter = ('profit_margin',)
    list_per_page = 20

    def average_cost(self, obj):
        return obj.get_average_cost()
    
    def selling_price(self, obj):
        return obj.get_selling_price()

    average_cost.short_description = "Avg Cost"
    selling_price.short_description = "Selling Price"