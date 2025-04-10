from django.db import models
from simple_history.models import HistoricalRecords

from purchase_invoice.models import PurchaseInvoice

class Payment(models.Model):
    purchase_invoice = models.ForeignKey(PurchaseInvoice, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    account = models.ForeignKey('account.Account', on_delete=models.CASCADE, related_name='payed_payments')
    payment_date = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    def __str__(self):
        return f"Payment {self.id} for Purchase {self.purchase_invoice.id}"
