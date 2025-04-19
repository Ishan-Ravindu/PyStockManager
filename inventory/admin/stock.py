from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum
from django.urls import reverse
from django.template.loader import render_to_string

from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin

from inventory.models.stock import Stock
from inventory.admin.filters import QuantityRangeFilter, PriceComparisonFilter


@admin.register(Stock)
class StockAdmin(SimpleHistoryAdmin, ModelAdmin):
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
    list_display_links = None  

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    def product_with_shops(self, obj):
        stocks = Stock.objects.filter(product=obj.product).select_related('shop', 'product')
        total_quantity = stocks.aggregate(total=Sum('quantity'))['total'] or 0

        context = {
            'product': obj.product,
            'stocks': stocks,
            'total_quantity': total_quantity,
        }

        html = render_to_string('admin/inventory/product_with_shops.html', context)
        return format_html(html)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        products = set()
        result_ids = []
        all_stocks = Stock.objects.all().select_related('product').order_by('product__name', '-quantity')
        for stock in all_stocks:
            if stock.product.id not in products:
                products.add(stock.product.id)
                result_ids.append(stock.id)
        return qs.filter(id__in=result_ids).order_by('product__name')

