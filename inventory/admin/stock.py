from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum, F
from django.contrib.admin import SimpleListFilter
from simple_history.admin import SimpleHistoryAdmin

from inventory.models.stock import Stock

class QuantityRangeFilter(SimpleListFilter):
    title = 'quantity range'
    parameter_name = 'quantity_range'

    def lookups(self, request, model_admin):
        return (
            ('0', 'Empty stock (0)'),
            ('1-10', 'Low stock (1-10)'),
            ('11-50', 'Medium stock (11-50)'),
            ('51-100', 'High stock (51-100)'),
            ('101+', 'Very high stock (101+)'),
        )

    def queryset(self, request, queryset):
        if self.value() == '0':
            return queryset.filter(quantity=0)
        elif self.value() == '1-10':
            return queryset.filter(quantity__range=(1, 10))
        elif self.value() == '11-50':
            return queryset.filter(quantity__range=(11, 50))
        elif self.value() == '51-100':
            return queryset.filter(quantity__range=(51, 100))
        elif self.value() == '101+':
            return queryset.filter(quantity__gte=101)
        return queryset

class PriceComparisonFilter(SimpleListFilter):
    title = 'price comparison'
    parameter_name = 'price_comparison'

    def lookups(self, request, model_admin):
        return (
            ('profit_positive', 'Profitable (Selling > Cost)'),
            ('profit_negative', 'Loss (Selling < Cost)'),
            ('profit_neutral', 'Break-even (Selling = Cost)'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'profit_positive':
            return queryset.filter(selling_price__gt=F('average_cost'))
        elif self.value() == 'profit_negative':
            return queryset.filter(selling_price__lt=F('average_cost'))
        elif self.value() == 'profit_neutral':
            return queryset.filter(selling_price=F('average_cost'))
        return queryset

@admin.register(Stock)
class StockAdmin(SimpleHistoryAdmin):
    list_display = ('product_with_shops',)
    list_filter = (
        'product',
        'shop',
        QuantityRangeFilter,
        PriceComparisonFilter,
    )
    search_fields = (
        'shop__name', 
        'shop__code',
        'product__name',
        'product__description',
    )
    list_per_page = 20

    def has_change_permission(self, request, obj=None):
        return False 
    def has_delete_permission(self, request, obj=None):
        return False
    def has_add_permission(self, request):
        return False

    def product_with_shops(self, obj):
        stocks = Stock.objects.filter(product=obj.product).select_related('shop', 'product')
        total_quantity = stocks.aggregate(total=Sum('quantity'))['total'] or 0
        
        html = f"""
        <table style="width:100%; border-collapse: collapse; table-layout: fixed;">
            <thead>
                <tr style="background-color: #f5f5f5;">
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: left; width: 25%;">Product</th>
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: left; width: 25%;">Shop</th>
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: right; width: 15%;">Quantity</th>
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: right; width: 15%;">Avg Cost</th>
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: right; width: 20%;">Selling Price</th>
                </tr>
            </thead>
            <tbody>
        """
        
        for i, stock in enumerate(stocks):
            html += f"""
            <tr style="background-color: {'#f9f9f9' if i % 2 else 'white'};">
                <td style="border: 1px solid #ddd; padding: 8px;{' font-weight: bold;' if i == 0 else ''}">
                    {stock.product.name if i == 0 else ''}
                </td>
                <td style="border: 1px solid #ddd; padding: 8px;">{stock.shop.name} {'(Warehouse)' if stock.shop.is_warehouse else ''}</td>
                <td style="border: 1px solid #ddd; padding: 8px; text-align: right; {'color: red;' if stock.quantity <= 0 else ''}">
                    {stock.quantity}
                </td>
                <td style="border: 1px solid #ddd; padding: 8px; text-align: right;">{stock.average_cost:.2f}</td>
                <td style="border: 1px solid #ddd; padding: 8px; text-align: right; color: {'green' if stock.selling_price > stock.average_cost else 'red' if stock.selling_price < stock.average_cost else 'black'}">
                    {stock.selling_price:.2f}
                </td>
            </tr>
            """
        
        html += f"""
            <tr style="background-color: #e6e6e6; font-weight: bold;">
                <td style="border: 1px solid #ddd; padding: 8px;"></td>
                <td style="border: 1px solid #ddd; padding: 8px;"></td>
                <td style="border: 1px solid #ddd; padding: 8px; color: {'red' if total_quantity <= 0 else 'black'}; text-align: right;">{total_quantity}</td>
                <td style="border: 1px solid #ddd; padding: 8px;"></td>
                <td style="border: 1px solid #ddd; padding: 8px;"></td>
            </tr>
            </tbody>
        </table>
        """
        
        return format_html(html)
    
    product_with_shops.short_description = 'Product Stock Across Shops'
    product_with_shops.allow_tags = True

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.order_by('product__name').distinct('product__name')