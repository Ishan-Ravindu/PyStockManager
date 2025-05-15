from django.db import models
from decimal import Decimal
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
        self.quantity += quantity_change
        self.save()
    
    def calculate_selling_price(self):
        try:
            cost = Decimal(self.average_cost)
            margin = Decimal(self.product.profit_margin)
            markup = cost * (margin / Decimal('100'))
            return cost + markup
        except Exception:
            return self.selling_price
    
    def save(self, *args, **kwargs):
        if self.pk:
            try:
                old_instance = Stock.objects.get(pk=self.pk)
                if old_instance.average_cost != self.average_cost:
                    self.selling_price = self.calculate_selling_price()
            except Stock.DoesNotExist:
                self.selling_price = self.calculate_selling_price()
        else:
            self.selling_price = self.calculate_selling_price()

        super().save(*args, **kwargs)