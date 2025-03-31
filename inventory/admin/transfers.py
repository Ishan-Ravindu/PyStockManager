from django.contrib import admin
from django.utils.html import format_html
from ..models import StockTransfer, StockTransferItem, Stock

class StockTransferItemInline(admin.TabularInline):
    model = StockTransferItem
    extra = 1
    
@admin.register(StockTransfer)
class StockTransferAdmin(admin.ModelAdmin):
    list_display = ('id', 'from_shop', 'to_shop', 'created_at')
    list_filter = ('from_shop', 'to_shop', 'created_at')
    search_fields = ('from_shop__name', 'to_shop__name')
    readonly_fields = ('created_at',)
    inlines = [StockTransferItemInline]