from django.db import models
from django.utils.html import format_html
from django.core.validators import RegexValidator

phone_regex = RegexValidator(
    regex=r'^0\d{9}$',
    message="Phone number must be in the format: '0XXXXXXXXX'. Exactly 10 digits starting with 0."
)

class Shop(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=255)
    location = models.TextField()
    is_warehouse = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name}({self.code})"

class Supplier(models.Model):
    name = models.CharField(max_length=255)
    mobile_number = models.CharField(validators=[phone_regex], max_length=10)
    address = models.TextField(null=True, blank=True)
    email = models.EmailField(max_length=254, null=True, blank=True)

    def __str__(self):
        return self.name

class Customer(models.Model):
    name = models.CharField(max_length=255)
    mobile_number = models.CharField(validators=[phone_regex], max_length=10)
    address = models.TextField(null=True, blank=True)
    email = models.EmailField(max_length=254, null=True, blank=True)
    credit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    credit_limit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    credit_period = models.IntegerField(default=0)
    black_list = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name}-({self.mobile_number}) - Credit: {self.credit}/{self.credit_limit} ({self.credit_period} days)"
    
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

class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    profit_margin = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)

    def __str__(self):
        return f'{self.name} - Latest selling Price : {self.get_selling_price()}'

    def get_average_cost(self):
        """Calculate the average cost of all purchase invoices."""
        from .purchases import PurchaseInvoiceItem
        purchase_items = PurchaseInvoiceItem.objects.filter(product=self)
        total_cost = sum(item.price * item.quantity for item in purchase_items)
        total_quantity = sum(item.quantity for item in purchase_items)

        return total_cost / total_quantity if total_quantity > 0 else 0

    def get_selling_price(self):
        """Calculate the selling price based on the profit margin."""
        average_cost = self.get_average_cost()
        return average_cost * (1 + self.profit_margin / 100)