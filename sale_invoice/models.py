from django.db import models
from simple_history.models import HistoricalRecords

class SalesInvoice(models.Model):
    customer = models.ForeignKey('customer.Customer', on_delete=models.SET_NULL, null=True)
    shop = models.ForeignKey('shop.Shop', on_delete=models.CASCADE)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, editable=False)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, editable=False)
    due_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    def __str__(self):
        return f"{self.shop.code}#{self.id} - ({self.paid_amount}/{self.total_amount})"
    
    class Meta:
        permissions = [
            ("can_view_icon_sale_invoice", "Can view icon sale invoice"),
        ]
    
    def update_total_amount(self):
        """Calculate and update total amount from sales invoice items, considering discounts.
        Both amount and percentage discounts are applied per unit."""
        total = 0
        for item in self.items.all():
            unit_price = item.price if item.price else 0            
            if item.discount_method == 'amount':
                discounted_unit_price = max(unit_price - item.discount_amount, 0)
            elif item.discount_method == 'percentage':
                discount_value = unit_price * (item.discount_amount / 100)
                discounted_unit_price = max(unit_price - discount_value, 0)
            else:
                discounted_unit_price = unit_price                
            line_total = discounted_unit_price * item.quantity
            total += line_total        
        self.total_amount = total
        self.save(update_fields=['total_amount'])
    
    def get_due_amount(self):
        """Calculate remaining due amount."""
        return self.total_amount - self.paid_amount
    
    def payment_status(self):
        from django.utils import timezone
        from django.utils.html import format_html
        
        if self.total_amount <= self.paid_amount:
            return format_html('<span style="color: green; font-weight: bold;">Paid</span>')
        elif self.due_date and self.due_date < timezone.now().date():
            return format_html('<span style="color: red; font-weight: bold;">Overdue</span>')
        elif self.paid_amount == 0:
            return format_html('<span style="color: orange; font-weight: bold;">Unpaid</span>')
        else:
            return format_html('<span style="color: blue; font-weight: bold;">Partially Paid</span>')
    payment_status.short_description = 'Status'

    def get_total_average_cost(self):
        """
        Calculate the sum of all average_cost values from all invoice items.
        Returns 0 if there are no items or all average_cost values are null.
        """
        total = 0
        for item in self.items.all():
            if item.average_cost is not None:
                total += item.average_cost*item.quantity
        return total

    def get_profit(self):
        """
        Calculate the profit of the invoice (total_amount - total_average_cost).
        """
        total_avg_cost = self.get_total_average_cost()
        return self.total_amount - total_avg_cost

class SalesInvoiceItem(models.Model):
    DISCOUNT_METHOD_CHOICES = [
        ('amount', 'Amount'),
        ('percentage', 'Percentage'),
    ]
    
    sales_invoice = models.ForeignKey(SalesInvoice, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('product.Product', on_delete=models.CASCADE)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    average_cost = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    discount_method = models.CharField(max_length=10, choices=DISCOUNT_METHOD_CHOICES, default='amount')
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    history = HistoricalRecords()
    
    def __str__(self):
        return f"{self.product.name}"
