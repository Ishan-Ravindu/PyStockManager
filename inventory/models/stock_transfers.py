from django.db import models
from django.forms import ValidationError
from simple_history.models import HistoricalRecords

class StockTransfer(models.Model):
    from_shop = models.ForeignKey('shop.Shop', on_delete=models.CASCADE, related_name='outgoing_transfers')
    to_shop = models.ForeignKey('shop.Shop', on_delete=models.CASCADE, related_name='incoming_transfers')
    description = models.CharField(max_length=255,blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    def clean(self):
        if self.from_shop and self.to_shop and self.from_shop == self.to_shop:
            raise ValidationError({"to_shop": "Cannot transfer stock to the same shop."})
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    class Meta:
        permissions = [
            ("can_view_icon_stock_transfer", "Can view icon stock transfer"),
        ]

class StockTransferItem(models.Model):
    stock_transfer = models.ForeignKey(StockTransfer, on_delete=models.CASCADE)
    product = models.ForeignKey('product.Product', on_delete=models.CASCADE)
    quantity = models.IntegerField()
    history = HistoricalRecords()