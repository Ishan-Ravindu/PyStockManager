from django.db import models

from entity.models import Product, Shop

class Stock(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.shop.name} - {self.product.name} ({self.quantity})"

    def update_stock(self, quantity_change):
        """Update stock with a controlled function (prevents direct admin changes)."""
        self.quantity += quantity_change
        self.save()