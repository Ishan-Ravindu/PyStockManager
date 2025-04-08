from django.db import models

from sale_invoice.models import SalesInvoice

class Receipt(models.Model):
    sales_invoice = models.ForeignKey(SalesInvoice, on_delete=models.CASCADE, related_name='receipts')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    account = models.ForeignKey('account.Account', on_delete=models.CASCADE, related_name='received_payments')
    received_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Receipt {self.id} for Sales {self.sales_invoice.id}"
