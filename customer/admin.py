from django.contrib import admin

from customer.models import Customer

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'mobile_number', 'address', 'credit', 'credit_limit', 
                   'credit_period', 'combined_status', 'black_list')
    list_filter = ('credit_period', 'black_list')
    search_fields = ('name', 'mobile_number')
    readonly_fields = ('credit',)
    list_per_page = 20
    
    fieldsets = (
        (None, {
            'fields': ('name', 'mobile_number', 'address')
        }),
        ('Credit Information', {
            'fields': ('credit', 'credit_limit', 'credit_period', 'black_list')
        }),
    )

