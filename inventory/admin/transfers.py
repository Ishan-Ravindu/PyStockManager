from django.contrib import admin
from django.utils.html import format_html
from ..models import StockTransfer, StockTransferItem, Stock

class StockTransferItemInline(admin.TabularInline):
    model = StockTransferItem
    extra = 1
    
    # Add these fields to display quantity information
    readonly_fields = ('available_quantity',)
    
    def available_quantity(self, obj):
        """
        Display the current stock quantities for the selected product
        in both source and destination shops.
        """
        if not obj.pk or not obj.product:
            return "Select a product to see available quantity"
        
        # Get source shop quantity
        source_stock = Stock.objects.filter(
            shop=obj.stock_transfer.from_shop,
            product=obj.product
        ).first()
        
        # Get destination shop quantity
        dest_stock = Stock.objects.filter(
            shop=obj.stock_transfer.to_shop,
            product=obj.product
        ).first()
        
        source_qty = source_stock.quantity if source_stock else 0
        dest_qty = dest_stock.quantity if dest_stock else 0
        
        return format_html(
            '<strong>Source ({}):</strong> {} units &nbsp;&nbsp; '
            '<strong>Destination ({}):</strong> {} units',
            obj.stock_transfer.from_shop.name, source_qty,
            obj.stock_transfer.to_shop.name, dest_qty
        )
    
    available_quantity.short_description = "Available Stock"

@admin.register(StockTransfer)
class StockTransferAdmin(admin.ModelAdmin):
    list_display = ('id', 'from_shop', 'to_shop', 'created_at')
    list_filter = ('from_shop', 'to_shop', 'created_at')
    search_fields = ('from_shop__name', 'to_shop__name')
    readonly_fields = ('created_at',)
    inlines = [StockTransferItemInline]
    
    class Media:
        js = ('admin/js/stock_transfer.js',)