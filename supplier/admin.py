from django.contrib import admin

from supplier.models import Supplier

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'mobile_number', 'payable')
    search_fields = ('name', 'mobile_number')
    readonly_fields = ('payable',)
    list_per_page = 20
