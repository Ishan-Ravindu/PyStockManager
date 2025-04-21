from django.db import models
from django.utils.html import format_html
from utils import phone_regex
from simple_history.models import HistoricalRecords

class Customer(models.Model):
    name = models.CharField(max_length=255)
    mobile_number = models.CharField(validators=[phone_regex], max_length=10, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    email = models.EmailField(max_length=254, null=True, blank=True)
    credit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    credit_limit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    credit_period = models.IntegerField(default=0)
    whole_sale = models.BooleanField(default=False)
    black_list = models.BooleanField(default=False)
    history = HistoricalRecords()

    def __str__(self):
        return f"{self.name}-({self.mobile_number})"
    
    def credit_status(self):
        if self.credit_limit <= 0:
            return format_html('<span style="color: green; font-weight: bold;">No Limit Set</span>')
        usage_percentage = (self.credit / self.credit_limit * 100) if self.credit_limit > 0 else 0
       
        if self.credit > self.credit_limit:
            percentage_text = str(round(usage_percentage, 1))
            return format_html('<span style="color: red; font-weight: bold;">Over Limit ({}%)</span>', percentage_text)
        elif self.credit == self.credit_limit:
            return format_html('<span style="color: orange; font-weight: bold;">Credit Full (100%)</span>')
        elif usage_percentage >= 75:
            percentage_text = str(round(usage_percentage, 1))
            return format_html('<span style="color: #FF8C00; font-weight: bold;">Near Limit ({}%)</span>', percentage_text)
        else:
            percentage_text = str(round(usage_percentage, 1))
            return format_html('<span style="color: green; font-weight: bold;">Available ({}%)</span>', percentage_text)
    credit_status.short_description = 'Credit Status'
    
    def payment_status(self):
        from django.utils import timezone
        unpaid_invoices = self.salesinvoice_set.filter(total_amount__gt=models.F('paid_amount'))
        overdue_invoices = unpaid_invoices.filter(due_date__lt=timezone.now().date())
        if overdue_invoices.exists():
            oldest_overdue = overdue_invoices.order_by('due_date').first()
            days_overdue = (timezone.now().date() - oldest_overdue.due_date).days
            return format_html('<span style="color: red; font-weight: bold;">Payment Overdue ({} days)</span>', days_overdue)
        upcoming_invoices = unpaid_invoices.filter(due_date__gte=timezone.now().date())
        if upcoming_invoices.exists():
            next_due = upcoming_invoices.order_by('due_date').first()
            days_until_due = (next_due.due_date - timezone.now().date()).days
            if days_until_due <= 7:
                return format_html('<span style="color: orange; font-weight: bold;">Payment Due Soon ({} days)</span>', days_until_due)
            else:
                return format_html('<span style="color: blue; font-weight: bold;">Payment Scheduled</span>')
        return format_html('<span style="color: green; font-weight: bold;">No Pending Payments</span>')
    payment_status.short_description = 'Payment Status'
    
    def combined_status(self):
        credit_status_value = self.credit_status()
        payment_status_value = self.payment_status()
        return format_html('{}<br>{}'.format(credit_status_value, payment_status_value))
    combined_status.short_description = 'Customer Status'
