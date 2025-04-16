from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin
from unfold.contrib.import_export.forms import ExportForm, ImportForm
from import_export.admin import ImportExportModelAdmin

from supplier.models import Supplier

@admin.register(Supplier)
class SupplierAdmin(SimpleHistoryAdmin, ModelAdmin, ImportExportModelAdmin):
    list_display = ('name', 'address', 'mobile_number', 'payable')
    search_fields = ('name', 'mobile_number')
    readonly_fields = ('payable',)
    list_per_page = 20
    import_form_class = ImportForm
    export_form_class = ExportForm