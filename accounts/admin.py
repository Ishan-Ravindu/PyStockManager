from django.contrib import admin
from .models import Account, Withdraw, AccountTransfer

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'balance')
    search_fields = ('name',)

@admin.register(Withdraw)
class WithdrawAdmin(admin.ModelAdmin):
    list_display = ('account', 'amount', 'withdrawn_at')
    list_filter = ('withdrawn_at', 'account')
    search_fields = ('account__name',)
    date_hierarchy = 'withdrawn_at'

@admin.register(AccountTransfer)
class AccountTransferAdmin(admin.ModelAdmin):
    list_display = ('from_account', 'to_account', 'amount', 'transferred_at')
    list_filter = ('transferred_at', 'from_account', 'to_account')
    search_fields = ('from_account__name', 'to_account__name')
    date_hierarchy = 'transferred_at'