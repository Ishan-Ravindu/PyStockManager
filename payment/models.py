from django.db import models
from simple_history.models import HistoricalRecords
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

from purchase_invoice.models import PurchaseInvoice

class Payment(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    payable = GenericForeignKey('content_type', 'object_id')

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    account = models.ForeignKey('account.Account', on_delete=models.CASCADE, related_name='payed_payments')
    payment_date = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    def __str__(self):
        return f"Payment {self.id}"

    class Meta:
        permissions = [
            ("can_view_icon_payment", "Can view icon payment"),
        ]
