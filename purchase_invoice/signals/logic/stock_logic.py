from decimal import Decimal
from django.db import transaction
from django.conf import settings
import logging

from inventory.models.stock import Stock
from purchase_invoice.models import PurchaseInvoice, PurchaseInvoiceItem

# Default markup percentage (can be moved to settings.py)
DEFAULT_MARKUP_PERCENTAGE = getattr(settings, 'DEFAULT_MARKUP_PERCENTAGE', Decimal('0.20'))

def capture_original_invoice_data(instance, logger):
    """
    Store the original shop and supplier values before a PurchaseInvoice is updated.
    
    Args:
        instance: The PurchaseInvoice instance being saved
        logger: Logger instance for recording operations
    """
    if instance.pk:
        try:
            original = PurchaseInvoice.objects.get(pk=instance.pk)
            instance._original_shop = original.shop
            instance._original_supplier = original.supplier
            instance._original_total_amount = original.total_amount
            logger.debug(f"Stored original data for purchase invoice {instance.pk}: "
                        f"shop={original.shop}, supplier={original.supplier}, "
                        f"total_amount={original.total_amount}")
        except PurchaseInvoice.DoesNotExist:
            logger.warning(f"Could not find original purchase invoice with ID {instance.pk}")
            pass


def process_invoice_shop_changes(instance, logger):
    """
    Process changes when a purchase invoice's shop is modified.
    
    Args:
        instance: The PurchaseInvoice instance that was updated
        logger: Logger instance for recording operations
    """
    # Check if we have the original shop and if it has changed
    if not hasattr(instance, '_original_shop'):
        return
        
    shop_changed = instance._original_shop != instance.shop
    
    if not shop_changed:
        return
    
    logger.info(f"Shop changed for purchase invoice {instance.pk} "
               f"from {instance._original_shop} to {instance.shop}")
    
    # Get all items for this invoice
    invoice_items = PurchaseInvoiceItem.objects.filter(purchase_invoice=instance)
    
    # For each item, adjust stock in both shops
    for item in invoice_items:
        with transaction.atomic():
            try:
                # Revert changes from original shop
                original_stock = Stock.objects.get(
                    shop=instance._original_shop, 
                    product=item.product
                )
                
                # Recalculate average cost by removing this item's contribution
                original_total_value = original_stock.average_cost * original_stock.quantity
                item_value = item.price * item.quantity
                
                # Remove item value from total and adjust quantity
                new_total_value = original_total_value - item_value
                new_quantity = original_stock.quantity - item.quantity
                
                # Update stock record
                original_stock.quantity = new_quantity
                if new_quantity > 0:
                    original_stock.average_cost = new_total_value / new_quantity
                # If quantity becomes 0, keep the last known average cost
                
                if original_stock.quantity < 0:
                    original_stock.quantity = 0
                    logger.warning(f"Preventing negative stock for "
                                  f"shop {instance._original_shop}, "
                                  f"product {item.product}")
                
                original_stock.save()
                logger.info(f"Removed {item.quantity} units from original shop, "
                           f"new average cost: {original_stock.average_cost}")
            except Stock.DoesNotExist:
                logger.warning(f"No stock record exists for "
                              f"shop {instance._original_shop}, "
                              f"product {item.product}")
                pass
                
            # Apply changes to new shop
            try:
                new_stock = Stock.objects.get(
                    shop=instance.shop, 
                    product=item.product
                )
                
                # Update quantity and recalculate average cost
                old_value = new_stock.average_cost * new_stock.quantity
                new_value = item.price * item.quantity
                new_total_quantity = new_stock.quantity + item.quantity
                
                if new_total_quantity > 0:
                    new_stock.average_cost = (old_value + new_value) / new_total_quantity
                # If somehow quantity becomes 0, keep the existing average cost
                
                new_stock.quantity = new_total_quantity
                new_stock.save()
                
                logger.info(f"Added {item.quantity} units to new shop, "
                           f"new average cost: {new_stock.average_cost}")
            except Stock.DoesNotExist:
                # Create new stock record if doesn't exist
                new_stock = Stock.objects.create(
                    shop=instance.shop,
                    product=item.product,
                    quantity=item.quantity,
                    average_cost=item.price,
                    selling_price=item.price * (Decimal('1.0') + DEFAULT_MARKUP_PERCENTAGE)
                )
                logger.info(f"Created new stock record in new shop with "
                           f"quantity: {item.quantity}, average cost: {item.price}")