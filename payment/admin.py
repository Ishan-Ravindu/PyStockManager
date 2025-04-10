from django.contrib import admin
from payment.models import Payment
from simple_history.admin import SimpleHistoryAdmin

@admin.register(Payment)
class PaymentAdmin(SimpleHistoryAdmin):
    list_display = ('id', 'purchase_invoice', 'amount', 'account', 'payment_date')
    list_filter = ('payment_date', 'account')
    readonly_fields = ('payment_date',)
