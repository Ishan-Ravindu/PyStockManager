from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from supplier.models import Supplier

@admin.register(Supplier)
class SupplierAdmin(SimpleHistoryAdmin):
    list_display = ('name', 'address', 'mobile_number', 'payable')
    search_fields = ('name', 'mobile_number')
    readonly_fields = ('payable',)
    list_per_page = 20
