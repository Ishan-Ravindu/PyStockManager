from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin
from django import forms
from .models import Payment
from django.core.exceptions import ValidationError

class PaymentForm(forms.ModelForm):
    purchase_invoice = forms.ModelChoiceField(
        queryset=None,
        required=False,
        label="Purchase Invoice"
    )
    expense = forms.ModelChoiceField(
        queryset=None,
        required=False,
        label="Expense"
    )

    class Meta:
        model = Payment
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        from .models import PurchaseInvoice
        from expense.models import Expense
        
        self.fields['purchase_invoice'].queryset = PurchaseInvoice.objects.all()
        self.fields['expense'].queryset = Expense.objects.all()
        self.fields['content_type'].queryset = ContentType.objects.filter(
            model__in=['purchaseinvoice', 'expense']
        ).order_by('model')
        if self.instance and self.instance.pk:
            if self.instance.content_type.model == 'purchaseinvoice':
                self.initial['purchase_invoice'] = self.instance.object_id
            elif self.instance.content_type.model == 'expense':
                self.initial['expense'] = self.instance.object_id

    def clean(self):
        cleaned_data = super().clean()
        content_type = cleaned_data.get('content_type')
        purchase_invoice = cleaned_data.get('purchase_invoice')
        expense = cleaned_data.get('expense')
        if content_type:
            if content_type.model == 'purchaseinvoice':
                if not purchase_invoice:
                    raise ValidationError({
                        'purchase_invoice': 'Please select a purchase invoice'
                    })
                cleaned_data['object_id'] = purchase_invoice.id
            elif content_type.model == 'expense':
                if not expense:
                    raise ValidationError({
                        'expense': 'Please select an expense'
                    })
                cleaned_data['object_id'] = expense.id
        if not content_type:
            raise ValidationError({
                'content_type': 'Please select a content type'
            })
        
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        content_type = self.cleaned_data.get('content_type')
        if content_type:
            if content_type.model == 'purchaseinvoice':
                instance.object_id = self.cleaned_data['purchase_invoice'].id
            elif content_type.model == 'expense':
                instance.object_id = self.cleaned_data['expense'].id
        
        if commit:
            instance.save()
            self.save_m2m()
        
        return instance

@admin.register(Payment)
class PaymentAdmin(SimpleHistoryAdmin, ModelAdmin):
    form = PaymentForm
    list_display = ['id', 'payable', 'amount', 'account', 'payment_date']
    list_filter = ['payment_date', 'account', 'content_type']
    search_fields = ['id', 'amount']
    
    fieldsets = (
        (None, {
            'fields': ('content_type', 'purchase_invoice', 'expense'),
        }),
        ("Account", {
            'fields': ('account', 'amount',)
        }),
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['content_type'].label = "Payment Type"
        return form
    
    class Media:
        css = {
            'all': ('admin/css/payment_admin.css',)
        }
        js = ('admin/js/payment_admin.js',)