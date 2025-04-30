from django.contrib import admin
from .models import Account, Withdraw, AccountTransfer
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin
from unfold.contrib.import_export.forms import ExportForm, ImportForm
from import_export.admin import ImportExportModelAdmin

@admin.register(Account)
class AccountAdmin(SimpleHistoryAdmin, ModelAdmin, ImportExportModelAdmin):
    list_display = ('name', 'balance')
    search_fields = ('name',)
    import_form_class = ImportForm
    export_form_class = ExportForm

@admin.register(Withdraw)
class WithdrawAdmin(SimpleHistoryAdmin, ModelAdmin):
    list_display = ('account', 'amount', 'withdrawn_at')
    list_filter = ('account', 'withdrawn_at')

    save_as = False
    save_on_top = False
    def has_change_permission(self, request, obj=None):
        return False 
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(AccountTransfer)
class AccountTransferAdmin(SimpleHistoryAdmin, ModelAdmin):
    list_display = ('from_account', 'to_account', 'amount', 'transferred_at')
    list_filter = ('from_account', 'to_account', 'transferred_at')

    save_as = False
    save_on_top = False
    def has_change_permission(self, request, obj=None):
        return False 
    def has_delete_permission(self, request, obj=None):
        return False
