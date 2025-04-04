from django.contrib import admin
from ..models import Stock

@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('shop', 'product', 'quantity')
    list_filter = ('shop', 'product')
    search_fields = ('shop__name', 'product__name')
    list_per_page = 20

    def get_readonly_fields(self, request, obj=None):
        return ('quantity',)
    
    save_as = False
    save_on_top = False
    def has_change_permission(self, request, obj=None):
        return False 
    def has_delete_permission(self, request, obj=None):
        return False
    def has_add_permission(self, request):
        return False