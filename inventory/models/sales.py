from django.db import models
from django.forms import ValidationError

from accounts.models import Account
from entity.models import Customer, Product, Shop

class SalesInvoice(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True)
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, editable=False)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, editable=False)
    due_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.shop.code}#{self.id} - ({self.paid_amount}/{self.total_amount})"
    
    def clean(self):
        super().clean()
        if self.customer and self.customer.black_list:
            raise ValidationError("Cannot create an invoice for a blacklisted customer.")
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        if self.receipts.exists():
            raise ValidationError("This invoice cannot be deleted because it has associated receipts.")
        super().delete(*args, **kwargs)

    def update_total_amount(self):
        """Calculate and update total amount from sales invoice items."""
        total = sum(item.price * item.quantity for item in self.items.all())
        self.total_amount = total
        self.save()
    
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
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    
    def __str__(self):
        return f"{self.product.name} - {self.quantity} pcs"

class Receipt(models.Model):
    sales_invoice = models.ForeignKey(SalesInvoice, on_delete=models.CASCADE, related_name='receipts')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    account = models.ForeignKey('accounts.Account', on_delete=models.CASCADE, related_name='received_payments')
    received_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Receipt {self.id} for Sales {self.sales_invoice.id}"
        
    def clean(self):
        """Validate that amount doesn't exceed the remaining unpaid amount."""
        if self.amount is not None and self.sales_invoice:
            remaining_amount = self.sales_invoice.total_amount - self.sales_invoice.paid_amount
            if self.pk:
                original_receipt = Receipt.objects.get(pk=self.pk)
                remaining_amount += original_receipt.amount  # Add back the original amount
                
            if self.amount > remaining_amount:
                raise ValidationError({
                    'amount': f'Receipt amount cannot exceed the remaining unpaid amount of {remaining_amount}.'
                })
        super().clean()

    def save(self, *args, **kwargs):
        """Save receipt after validation"""
        self.full_clean()
        super().save(*args, **kwargs)
