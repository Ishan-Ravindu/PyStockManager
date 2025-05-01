from django.db.models.signals import post_save
from django.dispatch import receiver
from decimal import Decimal

from inventory.models.stock import Stock
from product.models import Product

@receiver(post_save, sender=Product)
def update_stock_selling_price(sender, instance, **kwargs):
    """
    Signal handler to update selling_price for all related stocks
    whenever a product's profit_margin changes.
    """
    stocks = Stock.objects.filter(product=instance)
    
    for stock in stocks:
        new_selling_price = stock.average_cost + (
            (stock.average_cost * instance.profit_margin) / Decimal('100.0')
        )
        stock.selling_price = new_selling_price
        # Use save with update_fields to avoid triggering other signals
        stock.save(update_fields=['selling_price'])
