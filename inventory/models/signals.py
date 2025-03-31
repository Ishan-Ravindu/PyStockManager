from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver

from .inventory import Stock
from .purchases import PurchaseInvoiceItem
from .transfers import StockTransferItem
from .sales import SalesInvoiceItem

@receiver(post_save, sender=PurchaseInvoiceItem)
def update_stock_and_price_after_purchase(sender, instance, **kwargs):
    """Update stock and recalculate average cost after a purchase."""
    stock, created = Stock.objects.get_or_create(
        shop=instance.purchase_invoice.shop, 
        product=instance.product
    )
    stock.update_stock(instance.quantity)

@receiver(post_save, sender=PurchaseInvoiceItem)
@receiver(post_delete, sender=PurchaseInvoiceItem)
def recalculate_total_amount(sender, instance, **kwargs):
    """Update total amount of purchase invoice when items change."""
    instance.purchase_invoice.update_total_amount()

@receiver(post_save, sender=StockTransferItem)
def update_stock_after_transfer(sender, instance, **kwargs):
    from_stock = Stock.objects.get(
        shop=instance.stock_transfer.from_shop, 
        product=instance.product
    )
    to_stock, created = Stock.objects.get_or_create(
        shop=instance.stock_transfer.to_shop, 
        product=instance.product
    )
    
    from_stock.update_stock(-instance.quantity)
    to_stock.update_stock(instance.quantity)

@receiver(post_save, sender=SalesInvoiceItem)
def update_stock_after_sale(sender, instance, **kwargs):
    stock = Stock.objects.get(
        shop=instance.sales_invoice.shop, 
        product=instance.product
    )
    stock.update_stock(-instance.quantity)

@receiver(post_save, sender=SalesInvoiceItem)
@receiver(post_delete, sender=SalesInvoiceItem)
def recalculate_sales_total_amount(sender, instance, **kwargs):
    """Update total amount of sales invoice when items change."""
    if instance.sales_invoice:
        instance.sales_invoice.update_total_amount()

@receiver(pre_save, sender=SalesInvoiceItem)
def populate_sales_price(sender, instance, **kwargs):
    """Auto-populate price from product's selling price if not set."""
    if instance.price is None:
        instance.price = instance.product.get_selling_price()