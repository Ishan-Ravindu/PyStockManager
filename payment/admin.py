from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin

from .models import Payment
from .forms import PaymentForm


@admin.register(Payment)
class PaymentAdmin(SimpleHistoryAdmin, ModelAdmin):
    form = PaymentForm
    list_display = ['id', 'payable', 'amount', 'account', 'payment_date']
    list_filter = ['payment_date', 'account', 'content_type']
    search_fields = ['id', 'amount']
    
    class Media:
        js = ['payment/js/payment_admin.js']