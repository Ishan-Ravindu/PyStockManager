from django.db import models

class Stock(models.Model):
    shop = models.ForeignKey('shop.Shop', on_delete=models.CASCADE)
    product = models.ForeignKey('entity.Product', on_delete=models.CASCADE)
    quantity = models.IntegerField(default=0)
    average_cost = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ('shop', 'product')

    def __str__(self):
        return f"{self.shop.name} - {self.product.name} ({self.quantity})"

    def update_stock(self, quantity_change):
        """Update stock with a controlled function (prevents direct admin changes)."""
        self.quantity += quantity_change
        self.save()