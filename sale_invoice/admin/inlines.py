from unfold.admin import TabularInline
from sale_invoice.models import SalesInvoiceItem
from .forms import SalesInvoiceItemForm

class SalesInvoiceItemInline(TabularInline):
    model = SalesInvoiceItem
    form = SalesInvoiceItemForm
    extra = 0

    def get_formset(self, request, obj=None, **kwargs):
        FormSet = super().get_formset(request, obj, **kwargs)
        for attr in ['new_objects', 'changed_objects', 'deleted_objects']:
            if not hasattr(FormSet, attr):
                setattr(FormSet, attr, [])
        return FormSet
