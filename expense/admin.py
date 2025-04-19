from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin
from unfold.contrib.import_export.forms import ExportForm, ImportForm
from import_export.admin import ImportExportModelAdmin

from expense.models import Expense


@admin.register(Expense)
class ExpenseAdmin(SimpleHistoryAdmin, ModelAdmin, ImportExportModelAdmin):
    list_display = ('id', 'name', 'description', 'paid_amount', )
    search_fields = ('name', 'description')
    import_form_class = ImportForm
    export_form_class = ExportForm
