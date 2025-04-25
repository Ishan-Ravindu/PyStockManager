from unfold.admin import TabularInline
from sale_invoice.models import SalesInvoiceItem
from .forms import SalesInvoiceItemForm

class SalesInvoiceItemInline(TabularInline):
    model = SalesInvoiceItem
    form = SalesInvoiceItemForm
    exclude = ['average_cost']
    autocomplete_fields = ['product']
    extra = 0

