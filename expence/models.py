from django.db import models
from simple_history.models import HistoricalRecords
from django.contrib.contenttypes.fields import GenericRelation

class Expense(models.Model):
    name = models.CharField(max_length=100)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    payments = GenericRelation('payment.Payment')
    history = HistoricalRecords()

    def __str__(self):
        return f"{self.name}"

