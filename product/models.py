from django.db import models
from simple_history.models import HistoricalRecords

class Category(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    profit_margin = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)
    history = HistoricalRecords()
    
    class Meta:
        verbose_name_plural = "Categories"
    
    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    profit_margin = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    history = HistoricalRecords()

    def __str__(self):
        return f'{self.name}'
