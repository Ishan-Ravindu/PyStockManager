from django.db import models
from simple_history.models import HistoricalRecords

class Stock(models.Model):
    shop = models.ForeignKey('shop.Shop', on_delete=models.CASCADE)
    product = models.ForeignKey('product.Product', on_delete=models.CASCADE)
    quantity = models.IntegerField(default=0)
    average_cost = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    history = HistoricalRecords()

    class Meta:
        unique_together = ('shop', 'product')
        permissions = [
            ("can_view_icon_stock", "Can view icon stock"),
        ]

    def __str__(self):
        return f"{self.shop.name} - {self.product.name} ({self.quantity})"

    def update_stock(self, quantity_change):
        """Update stock with a controlled function (prevents direct admin changes)."""
        self.quantity += quantity_change
        self.save()