from django.contrib.admin import SimpleListFilter
from django.db import models

class PaymentStatusFilter(SimpleListFilter):
    title = 'Payment Status'
    parameter_name = 'payment_status'

    def lookups(self, request, model_admin):
        return (
            ('paid', 'Paid'),
            ('overdue', 'Overdue'),
            ('unpaid', 'Unpaid'),
            ('partial', 'Partially Paid'),
        )

    def queryset(self, request, queryset):
        from django.utils import timezone
        today = timezone.now().date()

        if self.value() == 'paid':
            return queryset.filter(total_amount__lte=models.F('paid_amount'))
        if self.value() == 'overdue':
            return queryset.filter(total_amount__gt=models.F('paid_amount'), due_date__lt=today)
        if self.value() == 'unpaid':
            return queryset.filter(paid_amount=0)
        if self.value() == 'partial':
            return queryset.filter(paid_amount__gt=0, total_amount__gt=models.F('paid_amount'))
