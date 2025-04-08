from django.db import models

class SalesInvoice(models.Model):
    customer = models.ForeignKey('entity.Customer', on_delete=models.SET_NULL, null=True)
    shop = models.ForeignKey('shop.Shop', on_delete=models.CASCADE)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, editable=False)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, editable=False)
    due_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.shop.code}#{self.id} - ({self.paid_amount}/{self.total_amount})"
    
    def update_total_amount(self):
        """Calculate and update total amount from sales invoice items."""
        total = sum(item.price * item.quantity for item in self.items.all())
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

class SalesInvoiceItem(models.Model):
    sales_invoice = models.ForeignKey(SalesInvoice, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('entity.Product', on_delete=models.CASCADE)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    
    def __str__(self):
        return f"{self.product.name} - {self.quantity} pcs"
