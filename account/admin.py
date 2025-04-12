from django.contrib import admin
from .models import Account, Withdraw, AccountTransfer
from simple_history.admin import SimpleHistoryAdmin

@admin.register(Account)
class AccountAdmin(SimpleHistoryAdmin):
    list_display = ('name', 'balance')
    search_fields = ('name',)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Withdraw)
class WithdrawAdmin(SimpleHistoryAdmin):
    list_display = ('account', 'amount', 'withdrawn_at')
    list_filter = ('account', 'withdrawn_at')
    date_hierarchy = 'withdrawn_at'

@admin.register(AccountTransfer)
class AccountTransferAdmin(SimpleHistoryAdmin):
    list_display = ('from_account', 'to_account', 'amount', 'transferred_at')
    list_filter = ('from_account', 'to_account', 'transferred_at')
    date_hierarchy = 'transferred_at'
