from decimal import Decimal
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.db import transaction
from django.conf import settings
import logging

from inventory.models.inventory import Stock
from inventory.models.purchases import PurchaseInvoice, PurchaseInvoiceItem

# Set up logger
logger = logging.getLogger(__name__)

# Default markup percentage (can be moved to settings.py)
DEFAULT_MARKUP_PERCENTAGE = getattr(settings, 'DEFAULT_MARKUP_PERCENTAGE', Decimal('0.20'))


@receiver(pre_save, sender=PurchaseInvoice)
def store_original_invoice_data(sender, instance, **kwargs):
    """
    Store the original shop values before a PurchaseInvoice is updated.
    
    This is necessary to correctly handle stock adjustments when the invoice's
    shop is changed.
    """
    if instance.pk:
        try:
            original = PurchaseInvoice.objects.get(pk=instance.pk)
            instance._original_shop = original.shop
        except PurchaseInvoice.DoesNotExist:
            pass


@receiver(post_save, sender=PurchaseInvoice)
def handle_invoice_shop_changes(sender, instance, created, **kwargs):
    """
    When a purchase invoice's shop is changed, update all associated items' stocks.
    
    This function:
    1. Reverses stock changes from the original shop
    2. Applies stock changes to the new shop
    3. Recalculates average costs
    """
    if created:
        return  # New invoices are handled by the PurchaseInvoiceItem signals
    
    # Check if we have the original shop and if it has changed
    if not hasattr(instance, '_original_shop'):
        return
        
    shop_changed = instance._original_shop != instance.shop
    
    if not shop_changed:
        return
    
    # Get all items for this invoice
    invoice_items = PurchaseInvoiceItem.objects.filter(purchase_invoice=instance)
    
    # For each item, adjust stock in both shops
    for item in invoice_items:
        with transaction.atomic():
            # Revert changes from original shop
            try:
                original_stock = Stock.objects.get(
                    shop=instance._original_shop, 
                    product=item.product
                )
                original_stock.quantity -= item.quantity
                if original_stock.quantity < 0:
                    original_stock.quantity = 0
                original_stock.save()
            except Stock.DoesNotExist:
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
                
                new_stock.quantity = new_total_quantity
                new_stock.save()
            except Stock.DoesNotExist:
                # Create new stock record if doesn't exist
                # Create with configurable markup
                Stock.objects.create(
                    shop=instance.shop,
                    product=item.product,
                    quantity=item.quantity,
                    average_cost=item.price,
                    selling_price=item.price * (Decimal('1.0') + DEFAULT_MARKUP_PERCENTAGE)
                )


@receiver(pre_save, sender=PurchaseInvoiceItem)
def store_original_item_data(sender, instance, **kwargs):
    """
    Store the original values before a PurchaseInvoiceItem is updated.
    
    This allows proper handling of stock quantities and average costs when
    item details change.
    """
    if instance.pk:
        try:
            original = PurchaseInvoiceItem.objects.get(pk=instance.pk)
            
            # Store all relevant original values
            instance._original_quantity = original.quantity
            instance._original_price = original.price
            instance._original_product = original.product
            instance._original_invoice = original.purchase_invoice
        except PurchaseInvoiceItem.DoesNotExist:
            pass


@receiver(post_save, sender=PurchaseInvoiceItem)
def update_stock_on_purchase_item_save(sender, instance, created, **kwargs):
    """
    Update stock when a purchase invoice item is created or updated.
    
    For new items:
    - Add to shop's stock quantity
    - Update average cost
    
    For updated items:
    - Handle product, quantity, or price changes
    - Recalculate average costs
    """
    shop = instance.purchase_invoice.shop
    product = instance.product
    
    if created:
        # Handle new items
        with transaction.atomic():
            try:
                stock = Stock.objects.get(shop=shop, product=product)
                
                # Update quantity and recalculate average cost
                old_value = stock.average_cost * stock.quantity
                new_value = instance.price * instance.quantity
                new_total_quantity = stock.quantity + instance.quantity
                
                if new_total_quantity > 0:
                    stock.average_cost = (old_value + new_value) / new_total_quantity
                
                stock.quantity = new_total_quantity
                stock.save()
            except Stock.DoesNotExist:
                # Create new stock if it doesn't exist
                # Create with configurable markup
                Stock.objects.create(
                    shop=shop,
                    product=product,
                    quantity=instance.quantity,
                    average_cost=instance.price,
                    selling_price=instance.price * (Decimal('1.0') + DEFAULT_MARKUP_PERCENTAGE)
                )
    else:
        # Handle updates to existing items
        if not hasattr(instance, '_original_quantity'):
            return
            
        # Check if the invoice changed
        invoice_changed = (hasattr(instance, '_original_invoice') and 
                          instance._original_invoice != instance.purchase_invoice)
        
        # Check if the product changed
        product_changed = (hasattr(instance, '_original_product') and 
                          instance._original_product != instance.product)
        
        with transaction.atomic():
            # If invoice or product changed, handle it specially
            if invoice_changed or product_changed:
                # First, revert the original item effects
                try:
                    original_shop = instance._original_invoice.shop
                    original_product = instance._original_product
                    
                    original_stock = Stock.objects.get(
                        shop=original_shop, 
                        product=original_product
                    )
                    original_stock.quantity -= instance._original_quantity
                    if original_stock.quantity < 0:
                        original_stock.quantity = 0
                    original_stock.save()
                except (Stock.DoesNotExist, AttributeError):
                    pass
                
                # Then add the new item effects
                try:
                    new_stock = Stock.objects.get(shop=shop, product=product)
                    
                    # Update quantity and recalculate average cost
                    old_value = new_stock.average_cost * new_stock.quantity
                    new_value = instance.price * instance.quantity
                    new_total_quantity = new_stock.quantity + instance.quantity
                    
                    if new_total_quantity > 0:
                        new_stock.average_cost = (old_value + new_value) / new_total_quantity
                    
                    new_stock.quantity = new_total_quantity
                    new_stock.save()
                except Stock.DoesNotExist:
                    # Create new stock if it doesn't exist
                    Stock.objects.create(
                        shop=shop,
                        product=product,
                        quantity=instance.quantity,
                        average_cost=instance.price,
                        selling_price=instance.price * Decimal('1.2')  # Default markup
                    )
            else:
                # Just a quantity or price change
                quantity_change = instance.quantity - instance._original_quantity
                price_changed = instance.price != instance._original_price
                
                if quantity_change != 0 or price_changed:
                    try:
                        stock = Stock.objects.get(shop=shop, product=product)
                        
                        if quantity_change != 0:
                            # Update quantity
                            stock.quantity += quantity_change
                        
                        if price_changed or quantity_change != 0:
                            # Recalculate average cost by removing old item value and adding new item value
                            old_value = stock.average_cost * stock.quantity
                            old_item_value = instance._original_price * instance._original_quantity
                            adjusted_old_value = old_value - old_item_value
                            
                            new_item_value = instance.price * instance.quantity
                            new_total_value = adjusted_old_value + new_item_value
                            
                            # Calculate new average cost
                            if stock.quantity > 0:
                                stock.average_cost = new_total_value / stock.quantity
                        
                        stock.save()
                    except Stock.DoesNotExist:
                        pass

    # Update the invoice total
    instance.purchase_invoice.update_total_amount()


@receiver(post_delete, sender=PurchaseInvoiceItem)
def update_stock_on_purchase_item_delete(sender, instance, **kwargs):
    """
    When a purchase invoice item is deleted, reverse the stock changes.
    
    This function:
    1. Reduces the stock quantity
    2. Updates the invoice total
    """
    with transaction.atomic():
        shop = instance.purchase_invoice.shop
        product = instance.product
        
        try:
            stock = Stock.objects.get(shop=shop, product=product)
            
            # Remove quantity
            stock.quantity -= instance.quantity
            
            # Ensure quantity doesn't go below 0
            if stock.quantity < 0:
                stock.quantity = 0
                
            stock.save()
        except Stock.DoesNotExist:
            pass
            
        # Update the invoice total
        instance.purchase_invoice.update_total_amount()