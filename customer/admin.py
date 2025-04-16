from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin
from unfold.contrib.import_export.forms import ExportForm, ImportForm
from import_export.admin import ImportExportModelAdmin

from customer.models import Customer

@admin.register(Customer)
class CustomerAdmin(SimpleHistoryAdmin, ModelAdmin, ImportExportModelAdmin):
    list_display = ('name', 'mobile_number', 'address', 'credit', 'credit_limit', 
                   'credit_period', 'combined_status', 'black_list')
    list_filter = ('credit_period', 'black_list')
    search_fields = ('name', 'mobile_number')
    readonly_fields = ('credit',)
    list_per_page = 20
    import_form_class = ImportForm
    export_form_class = ExportForm
    
    fieldsets = (
        (None, {
            'fields': ('name', 'mobile_number', 'address')
        }),
        ('Credit Information', {
            'fields': ('credit', 'credit_limit', 'credit_period', 'black_list')
        }),
    )

