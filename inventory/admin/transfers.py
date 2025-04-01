from django.contrib import admin
from django.utils.html import format_html
from django import forms
from django.core.exceptions import ValidationError
from ..models import StockTransfer, StockTransferItem, Stock

class StockTransferItemInlineFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()

        if not hasattr(self.instance, 'from_shop') or not self.instance.from_shop:
            return

        product_quantities = {}

        for form in self.forms:
            if not form.is_valid() or form.cleaned_data.get('DELETE', False):
                continue
                
            product = form.cleaned_data.get('product')
            quantity = form.cleaned_data.get('quantity') or 0
            
            if not product or quantity <= 0:
                continue

            product_quantities[product] = product_quantities.get(product, 0) + quantity

        stock_map = {
            (stock.product, stock.shop): stock.quantity
            for stock in Stock.objects.filter(shop=self.instance.from_shop, product__in=product_quantities.keys())
        }

        for product, total_quantity in product_quantities.items():
            available_stock = stock_map.get((product, self.instance.from_shop), 0)
            if total_quantity > available_stock:
                raise ValidationError(
                    f"Insufficient stock for '{product}' in {self.instance.from_shop}. "
                    f"Available: {available_stock}, Requested: {total_quantity}"
                )

class StockTransferItemInline(admin.TabularInline):
    model = StockTransferItem
    extra = 1
    formset = StockTransferItemInlineFormSet

class StockTransferAdminForm(forms.ModelForm):
    class Meta:
        model = StockTransfer
        fields = '__all__'
    
    def clean(self):
        cleaned_data = super().clean()
        from_shop = cleaned_data.get('from_shop')
        to_shop = cleaned_data.get('to_shop')

        if from_shop and to_shop and from_shop == to_shop:
            raise ValidationError({"to_shop": "Cannot transfer stock to the same shop."})
        
        return cleaned_data

@admin.register(StockTransfer)
class StockTransferAdmin(admin.ModelAdmin):
    form = StockTransferAdminForm
    list_display = ('id', 'from_shop', 'to_shop', 'description', 'created_at')
    list_filter = ('from_shop', 'to_shop', 'created_at')
    search_fields = ('from_shop__name', 'to_shop__name')
    readonly_fields = ('created_at',)
    inlines = [StockTransferItemInline]
    save_as = False
    save_on_top = False

    def has_change_permission(self, request, obj=None):
        return False 

    def has_delete_permission(self, request, obj=None):
        return False
