from django.contrib import admin
from ..models import Stock

@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('shop', 'product', 'quantity')
    list_filter = ('shop', 'product')
    search_fields = ('shop__name', 'product__name')

    def get_readonly_fields(self, request, obj=None):
        return ('quantity',)

    def has_add_permission(self, request):
        return False