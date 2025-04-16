from django import forms
from django.contrib.contenttypes.models import ContentType
from payment.models import Payment
from expence.models import Expense
from purchase_invoice.models import PurchaseInvoice


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        allowed_models = [PurchaseInvoice, Expense]
        self.fields['content_type'].queryset = ContentType.objects.filter(
            model__in=[model._meta.model_name for model in allowed_models],
        )
        self.fields['content_type'].label = "Payment Type"
        self.fields['content_type'].label_from_instance = self.get_content_type_label

        self.fields['object_id'] = forms.ChoiceField(
            required=True,
            label="Select Item"
        )

    def get_content_type_label(self, obj):
        model_name = obj.model
        if model_name == 'purchaseinvoice':
            return 'Purchase'
        elif model_name == 'expense':
            return 'Expense'
        return model_name.capitalize()