from django import forms
from django.forms.models import BaseInlineFormSet
from django.utils import timezone
from sale_invoice.models import SalesInvoice, SalesInvoiceItem
from .validators import CustomerValidator, InventoryValidator, InvoiceValidator

class SalesInvoiceForm(forms.ModelForm):
    class Meta:
        model = SalesInvoice
        fields = '__all__'
        exclude = ('created_at',)

    def clean(self):
        cleaned_data = super().clean()
        customer = cleaned_data.get('customer')
        due_date = cleaned_data.get('due_date')
        today = timezone.now().date()

        try:
            CustomerValidator.validate_blacklist(customer)
        except forms.ValidationError as e:
            self.add_error(None, e)

        if customer and due_date:
            try:
                CustomerValidator.validate_due_date(due_date, customer, today)
            except forms.ValidationError as e:
                self.add_error('due_date', e)

        return cleaned_data

class SalesInvoiceItemFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        
        if not self.forms:
            raise forms.ValidationError("Invoice must have at least one valid item.")

class SalesInvoiceItemForm(forms.ModelForm):
    class Meta:
        model = SalesInvoiceItem
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get('product')
        quantity = cleaned_data.get('quantity')
        price = cleaned_data.get('price')
        sales_invoice = cleaned_data.get('sales_invoice')
        shop = sales_invoice.shop if sales_invoice else None

        if not shop and hasattr(self, 'parent_form'):
            parent_data = self.parent_form.cleaned_data
            shop = parent_data.get('shop')
        
        if product and quantity and shop:
            original_quantity = 0
            original_product = None            
            if self.instance and self.instance.pk:
                try:
                    original = self.instance.__class__.objects.get(pk=self.instance.pk)
                    original_quantity = original.quantity
                    original_product = original.product
                except self.instance.__class__.DoesNotExist:
                    pass
            if original_product and original_product == product:
                quantity_difference = quantity - original_quantity
                if quantity_difference <= 0:
                    # Even if quantity is reduced, we should still validate the price
                    if price and product and shop:
                        try:
                            InventoryValidator.validate_price_not_below_selling_price(None, product, price, shop)
                        except forms.ValidationError as e:
                            self.add_error('price', e)
                    return cleaned_data
                try:
                    InventoryValidator.validate_stock_quantity(product, quantity_difference, shop)
                except forms.ValidationError as e:
                    self.add_error('quantity', e)
            else:
                try:
                    InventoryValidator.validate_stock_quantity(product, quantity, shop)
                except forms.ValidationError as e:
                    self.add_error('quantity', e)
            if price and product and shop:
                try:
                    InventoryValidator.validate_price_not_below_selling_price(None, product, price, shop)
                except forms.ValidationError as e:
                    self.add_error('price', e)

        return cleaned_data