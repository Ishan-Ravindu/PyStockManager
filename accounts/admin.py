from django.contrib import admin
from .models import Account, Withdraw, AccountTransfer, AccountTransactionHistory

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'balance')
    search_fields = ('name',)

@admin.register(Withdraw)
class WithdrawAdmin(admin.ModelAdmin):
    list_display = ('account', 'amount', 'withdrawn_at')
    list_filter = ('account', 'withdrawn_at')
    date_hierarchy = 'withdrawn_at'

@admin.register(AccountTransfer)
class AccountTransferAdmin(admin.ModelAdmin):
    list_display = ('from_account', 'to_account', 'amount', 'transferred_at')
    list_filter = ('from_account', 'to_account', 'transferred_at')
    date_hierarchy = 'transferred_at'

@admin.register(AccountTransactionHistory)
class AccountTransactionHistoryAdmin(admin.ModelAdmin):
    list_display = ('account', 'description', 'transaction_type', 'action_type', 'amount', 
                    'previous_balance', 'new_balance', 'timestamp')
    list_filter = ('account', 'transaction_type', 'action_type', 'timestamp')
    search_fields = ('description', 'account__name')
    date_hierarchy = 'timestamp'
    readonly_fields = ('account', 'amount', 'previous_balance', 'new_balance', 
                       'transaction_type', 'action_type', 'content_type', 
                       'object_id', 'description', 'timestamp')
    
    def has_add_permission(self, request):
        # Prevent manual creation of history entries
        return False
    
    def has_change_permission(self, request, obj=None):
        # Prevent editing of history entries
        return False