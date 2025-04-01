from django.db import models
from django.forms import ValidationError
from .base import Customer, Shop, Product

class SalesInvoice(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True)
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE)
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
        self.save()
    
    def get_due_amount(self):
        """Calculate remaining due amount."""
        return self.total_amount - self.paid_amount

class SalesInvoiceItem(models.Model):
    sales_invoice = models.ForeignKey(SalesInvoice, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    
    def __str__(self):
        return f"{self.product.name} - {self.quantity} pcs"

class Receipt(models.Model):
    sales_invoice = models.ForeignKey(SalesInvoice, on_delete=models.CASCADE, related_name='receipts')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50, choices=[
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('bank_transfer', 'Bank Transfer')
    ])
    received_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Receipt {self.id} for Sales {self.sales_invoice.id}"
        
    def clean(self):
        """Validate that amount doesn't exceed the remaining unpaid amount."""
        if self.amount is not None and self.sales_invoice:
            remaining_amount = self.sales_invoice.total_amount - self.sales_invoice.paid_amount
            if self.amount > remaining_amount:
                raise ValidationError({
                    'amount': f'Receipt amount cannot exceed the remaining unpaid amount of {remaining_amount}.'
                })
        super().clean()

    def save(self, *args, **kwargs):
        """Update paid amount in SalesInvoice and reduce customer's credit when a receipt is created."""
        self.full_clean()  # Run validation before saving
        super().save(*args, **kwargs)
        self.sales_invoice.paid_amount += self.amount
        self.sales_invoice.save()
        
        # Reduce customer's credit
        if self.sales_invoice.customer:
            self.sales_invoice.customer.credit -= self.amount
            self.sales_invoice.customer.save()
