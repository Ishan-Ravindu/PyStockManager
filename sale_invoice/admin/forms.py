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
        if self.instance.pk:
                    items_count = self.instance.salesinvoiceitem_set.count()
        else:
            items_count =  0
            try:
                InvoiceValidator.validate_has_items(items_count)
            except forms.ValidationError as e:
                self.add_error(None, e)

            return cleaned_data

class SalesInvoiceItemForm(forms.ModelForm):
    class Meta:
        model = SalesInvoiceItem
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get('product')
        quantity = cleaned_data.get('quantity')
        shop = getattr(getattr(self, 'parent_instance', None), 'shop', None)

        if product and quantity and shop:
            try:
                InventoryValidator.validate_stock_quantity(product, quantity, shop)
            except forms.ValidationError as e:
                self.add_error('quantity', e)

        return cleaned_data

