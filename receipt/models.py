from django.db import models
from simple_history.models import HistoricalRecords

from sale_invoice.models import SalesInvoice

class Receipt(models.Model):
    sales_invoice = models.ForeignKey(SalesInvoice, on_delete=models.CASCADE, related_name='receipts')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    account = models.ForeignKey('account.Account', on_delete=models.CASCADE, related_name='received_payments')
    received_at = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    def __str__(self):
        return f"Receipt {self.id} for Sales {self.sales_invoice.id}"
    
    class Meta:
        permissions = [
            ("can_view_icon_receipt", "Can view icon receipt"),
        ]
