from django.db import models
from .base import Shop, Product

class StockTransfer(models.Model):
    from_shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='outgoing_transfers')
    to_shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='incoming_transfers')
    created_at = models.DateTimeField(auto_now_add=True)

class StockTransferItem(models.Model):
    stock_transfer = models.ForeignKey(StockTransfer, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()