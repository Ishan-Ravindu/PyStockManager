from django.db import models
from simple_history.models import HistoricalRecords

class Shop(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=255)
    location = models.TextField()
    is_warehouse = models.BooleanField(default=False)
    history = HistoricalRecords()

    def __str__(self):
        return f"{self.code}"