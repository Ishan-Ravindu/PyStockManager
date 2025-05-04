from unfold.admin import TabularInline
from sale_invoice.models import SalesInvoiceItem
from .forms import SalesInvoiceItemForm, SalesInvoiceItemFormSet

class SalesInvoiceItemInline(TabularInline):
    model = SalesInvoiceItem
    form = SalesInvoiceItemForm
    formset = SalesInvoiceItemFormSet
    exclude = ['average_cost']
    autocomplete_fields = ['product']
    extra = 0
    
    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        formset.parent_obj = obj
        return formset

    def get_extra(self, request, obj=None, **kwargs):
        if obj is not None:
            return 0
        return self.extra