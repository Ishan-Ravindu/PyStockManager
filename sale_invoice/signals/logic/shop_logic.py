from decimal import Decimal
from django.db import transaction
from inventory.models.stock import Stock
from sale_invoice.models import SalesInvoiceItem

def process_invoice_shop_change(instance, logger):
    """
    Process shop changes on a sales invoice.
    
    Args:
        instance: The SalesInvoice instance that was updated
        logger: Logger instance for recording operations
    """
    # We only care about shop changes for existing invoices
    if not hasattr(instance, '_original_shop'):
        return
        
    shop_changed = instance._original_shop != instance.shop
    
    if not shop_changed:
        return
    
    # Get all items for this invoice
    invoice_items = SalesInvoiceItem.objects.filter(sales_invoice=instance)
    
    # For each item, adjust stock in both shops
    for item in invoice_items:
        with transaction.atomic():
            try:
                # Return stock to original shop
                original_stock = Stock.objects.get(
                    shop=instance._original_shop, 
                    product=item.product
                )
                original_stock.quantity += item.quantity
                original_stock.save()
                logger.info(f"Returned {item.quantity} to stock for product {item.product} in original shop {instance._original_shop}")
            except Stock.DoesNotExist:
                Stock.objects.create(
                    shop=instance._original_shop,
                    product=item.product,
                    quantity=item.quantity,
                    average_cost=Decimal('0.00'),
                    selling_price=Decimal('0.00')
                )
                logger.warning(f"Created new stock record in original shop with returned quantity")
            
            try:
                # Reduce stock in new shop
                new_stock = Stock.objects.get(
                    shop=instance.shop, 
                    product=item.product
                )
                
                # Check if there's enough stock
                if new_stock.quantity < item.quantity:
                    logger.warning(f"Insufficient stock for product {item.product} in new shop {instance.shop}. "
                                 f"Available: {new_stock.quantity}, Requested: {item.quantity}")
                
                new_stock.quantity -= item.quantity
                if new_stock.quantity < 0:
                    new_stock.quantity = 0
                new_stock.save()
                logger.info(f"Stock reduced by {item.quantity} for product {item.product} in new shop {instance.shop}")
            except Stock.DoesNotExist:
                logger.error(f"No stock record found for product {item.product} in new shop {instance.shop}")