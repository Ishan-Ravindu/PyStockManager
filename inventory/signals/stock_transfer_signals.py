from decimal import Decimal
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.dispatch import receiver
from django.db import transaction
import logging

from inventory.models.inventory import Stock
from inventory.models.transfers import StockTransfer, StockTransferItem

# Set up logger
logger = logging.getLogger(__name__)


@receiver(pre_save, sender=StockTransfer)
def store_original_transfer_data(sender, instance, **kwargs):
    """
    Store the original shop values before a StockTransfer is updated.
    
    This allows proper handling of stock quantities when transfer source 
    or destination shops are changed.
    """
    if instance.pk:
        try:
            original = StockTransfer.objects.get(pk=instance.pk)
            instance._original_from_shop = original.from_shop
            instance._original_to_shop = original.to_shop
        except StockTransfer.DoesNotExist:
            # Instance might have been deleted
            pass


@receiver(post_save, sender=StockTransfer)
def handle_transfer_shop_changes(sender, instance, created, **kwargs):
    """
    When a stock transfer's shops are changed, update all associated items.
    
    This function:
    1. Reverses stock changes from the original shops
    2. Applies stock changes to the new shops
    3. Handles creation of new stock records when needed
    """
    if created:
        return  # No need to handle shop changes for new transfers
        
    # Check if we have the original shops and if they've changed
    has_original_data = hasattr(instance, '_original_from_shop') and hasattr(instance, '_original_to_shop')
    if not has_original_data:
        return        
        
    shops_changed = (instance._original_from_shop != instance.from_shop or 
                     instance._original_to_shop != instance.to_shop)    
    if not shops_changed:
        return
        
    # Process each transfer item
    transfer_items = StockTransferItem.objects.filter(stock_transfer=instance)
    for item in transfer_items:
        with transaction.atomic():
            # Return stock to original source shop
            try:
                original_from_stock = Stock.objects.get(
                    shop=instance._original_from_shop, 
                    product=item.product
                )
                original_from_stock.quantity += item.quantity
                original_from_stock.save()
            except Stock.DoesNotExist:
                pass
                
            # Remove stock from original destination shop
            try:
                original_to_stock = Stock.objects.get(
                    shop=instance._original_to_shop, 
                    product=item.product
                )
                original_to_stock.quantity -= item.quantity
                if original_to_stock.quantity < 0:
                    original_to_stock.quantity = 0
                original_to_stock.save()
            except Stock.DoesNotExist:
                pass
                
            # Remove stock from new source shop
            try:
                new_from_stock = Stock.objects.get(
                    shop=instance.from_shop, 
                    product=item.product
                )
                new_from_stock.quantity -= item.quantity
                if new_from_stock.quantity < 0:
                    new_from_stock.quantity = 0
                new_from_stock.save()
            except Stock.DoesNotExist:
                pass
                
            # Add stock to new destination shop
            try:
                new_to_stock = Stock.objects.get(
                    shop=instance.to_shop, 
                    product=item.product
                )
                new_to_stock.quantity += item.quantity
                new_to_stock.save()
            except Stock.DoesNotExist:
                # Create new stock record if doesn't exist in destination shop
                try:
                    new_from_stock = Stock.objects.get(
                        shop=instance.from_shop, 
                        product=item.product
                    )
                    Stock.objects.create(
                        shop=instance.to_shop,
                        product=item.product,
                        quantity=item.quantity,
                        average_cost=new_from_stock.average_cost,
                        selling_price=new_from_stock.selling_price
                    )
                except Stock.DoesNotExist:
                    # Create with default values if source stock doesn't exist
                    Stock.objects.create(
                        shop=instance.to_shop,
                        product=item.product,
                        quantity=item.quantity,
                        average_cost=Decimal('0.00'),
                        selling_price=Decimal('0.00')
                    )


@receiver(pre_save, sender=StockTransferItem)
def store_original_item_data(sender, instance, **kwargs):
    """
    Store the original quantity and product before a StockTransferItem is updated.
    
    This allows proper handling of stock quantities when item details change.
    """
    if instance.pk:
        try:
            original = StockTransferItem.objects.get(pk=instance.pk)
            instance._original_quantity = original.quantity            
            instance._original_product = original.product
        except StockTransferItem.DoesNotExist:
            pass


@receiver(post_save, sender=StockTransferItem)
def update_stock_on_transfer_item_save(sender, instance, created, **kwargs):
    """
    Update stock quantities when a transfer item is created or updated.
    
    For new items:
    - Decrease quantity from source shop
    - Increase quantity in destination shop
    
    For updated items:
    - Adjust quantities based on the quantity change
    - Create new stock records when needed
    - Handle product changes
    """
    if not created:
        # Handle updates to existing items
        product_changed = (hasattr(instance, '_original_product') and 
                          instance._original_product != instance.product)
        
        if hasattr(instance, '_original_quantity'):
            quantity_change = instance.quantity - instance._original_quantity
            if quantity_change == 0 and not product_changed:
                return  # No relevant changes
                
            with transaction.atomic():
                try:
                    # If product changed, handle both products
                    if product_changed:
                        logger.info(f"Product changed in transfer item {instance.pk} "
                                   f"from {instance._original_product} to {instance.product}")
                        
                        # Revert changes for original product
                        try:
                            original_from_stock = Stock.objects.get(
                                shop=instance.stock_transfer.from_shop, 
                                product=instance._original_product
                            )
                            original_from_stock.quantity += instance._original_quantity
                            original_from_stock.save()
                            
                            logger.info(f"Reverted {instance._original_quantity} units "
                                       f"to shop {instance.stock_transfer.from_shop} "
                                       f"for product {instance._original_product}")
                        except Stock.DoesNotExist:
                            logger.warning(f"Could not find stock record for "
                                          f"shop {instance.stock_transfer.from_shop}, "
                                          f"product {instance._original_product}")
                        
                        try:
                            original_to_stock = Stock.objects.get(
                                shop=instance.stock_transfer.to_shop, 
                                product=instance._original_product
                            )
                            original_to_stock.quantity -= instance._original_quantity
                            if original_to_stock.quantity < 0:
                                logger.warning(f"Negative stock prevented for "
                                              f"shop {instance.stock_transfer.to_shop}, "
                                              f"product {instance._original_product}")
                                original_to_stock.quantity = 0
                            original_to_stock.save()
                        except Stock.DoesNotExist:
                            logger.warning(f"Could not find stock record for "
                                          f"shop {instance.stock_transfer.to_shop}, "
                                          f"product {instance._original_product}")
                        
                        # Apply changes for new product
                        try:
                            from_stock = Stock.objects.get(
                                shop=instance.stock_transfer.from_shop, 
                                product=instance.product
                            )
                            # Validate sufficient stock before decrementing
                            if from_stock.quantity < instance.quantity:
                                logger.warning(f"Insufficient stock for product {instance.product} "
                                             f"in shop {instance.stock_transfer.from_shop}. "
                                             f"Available: {from_stock.quantity}, "
                                             f"Requested: {instance.quantity}")
                            
                            from_stock.quantity -= instance.quantity
                            if from_stock.quantity < 0:
                                from_stock.quantity = 0
                            from_stock.save()
                        except Stock.DoesNotExist:
                            logger.warning(f"No stock record exists for "
                                          f"shop {instance.stock_transfer.from_shop}, "
                                          f"product {instance.product}")
                        
                        try:
                            to_stock = Stock.objects.get(
                                shop=instance.stock_transfer.to_shop, 
                                product=instance.product
                            )
                            to_stock.quantity += instance.quantity
                            to_stock.save()
                        except Stock.DoesNotExist:
                            # Create new stock record
                            try:
                                from_stock = Stock.objects.get(
                                    shop=instance.stock_transfer.from_shop, 
                                    product=instance.product
                                )
                                Stock.objects.create(
                                    shop=instance.stock_transfer.to_shop,
                                    product=instance.product,
                                    quantity=instance.quantity,
                                    average_cost=from_stock.average_cost,
                                    selling_price=from_stock.selling_price
                                )
                                logger.info(f"Created new stock record for "
                                           f"shop {instance.stock_transfer.to_shop}, "
                                           f"product {instance.product}")
                            except Stock.DoesNotExist:
                                Stock.objects.create(
                                    shop=instance.stock_transfer.to_shop,
                                    product=instance.product,
                                    quantity=instance.quantity,
                                    average_cost=Decimal('0.00'),
                                    selling_price=Decimal('0.00')
                                )
                                logger.warning(f"Created new stock record with default values for "
                                              f"shop {instance.stock_transfer.to_shop}, "
                                              f"product {instance.product}")
                    else:
                        # Just a quantity change
                        # Update source shop stock
                        try:
                            from_stock = Stock.objects.get(
                                shop=instance.stock_transfer.from_shop, 
                                product=instance.product
                            )
                            # Validate stock level if quantity is increasing
                            if quantity_change > 0 and from_stock.quantity < quantity_change:
                                logger.warning(f"Insufficient stock for additional transfer. "
                                             f"Available: {from_stock.quantity}, "
                                             f"Additional requested: {quantity_change}")
                                
                            from_stock.quantity -= quantity_change
                            if from_stock.quantity < 0:
                                logger.warning(f"Preventing negative stock for "
                                              f"shop {instance.stock_transfer.from_shop}, "
                                              f"product {instance.product}")
                                from_stock.quantity = 0
                            from_stock.save()
                        except Stock.DoesNotExist:
                            logger.warning(f"No stock record exists for "
                                          f"shop {instance.stock_transfer.from_shop}, "
                                          f"product {instance.product}")
                            
                        # Update destination shop stock
                        try:
                            to_stock = Stock.objects.get(
                                shop=instance.stock_transfer.to_shop, 
                                product=instance.product
                            )
                            to_stock.quantity += quantity_change
                            to_stock.save()
                            
                            logger.info(f"Updated destination stock for "
                                       f"shop {instance.stock_transfer.to_shop}, "
                                       f"product {instance.product}, "
                                       f"change: {quantity_change}")
                        except Stock.DoesNotExist:
                            # Create new stock record if doesn't exist and quantity increased
                            if quantity_change > 0:
                                try:
                                    from_stock = Stock.objects.get(
                                        shop=instance.stock_transfer.from_shop, 
                                        product=instance.product
                                    )
                                    Stock.objects.create(
                                        shop=instance.stock_transfer.to_shop,
                                        product=instance.product,
                                        quantity=quantity_change,
                                        average_cost=from_stock.average_cost,
                                        selling_price=from_stock.selling_price
                                    )
                                    logger.info(f"Created new stock record for "
                                               f"shop {instance.stock_transfer.to_shop}, "
                                               f"product {instance.product}")
                                except Stock.DoesNotExist:
                                    Stock.objects.create(
                                        shop=instance.stock_transfer.to_shop,
                                        product=instance.product,
                                        quantity=quantity_change,
                                        average_cost=Decimal('0.00'),
                                        selling_price=Decimal('0.00')
                                    )
                                    logger.warning(f"Created new stock record with default values for "
                                                  f"shop {instance.stock_transfer.to_shop}, "
                                                  f"product {instance.product}")
                except Exception as e:
                    logger.error(f"Error updating stock on transfer item save: {str(e)}")
                    raise  # Re-raise the exception after logging
        return

    # Handle new transfer items
    with transaction.atomic():
        product = instance.product
        quantity = instance.quantity
        from_shop = instance.stock_transfer.from_shop
        to_shop = instance.stock_transfer.to_shop
        
        # Decrease stock in source shop
        try:
            from_stock = Stock.objects.get(shop=from_shop, product=product)
            from_stock.quantity -= quantity
            if from_stock.quantity < 0:
                from_stock.quantity = 0
            from_stock.save()
        except Stock.DoesNotExist:
            pass
            
        # Increase stock in destination shop
        try:
            to_stock = Stock.objects.get(shop=to_shop, product=product)
            to_stock.quantity += quantity
            to_stock.save()
        except Stock.DoesNotExist:
            # Create new stock record if doesn't exist in destination shop
            try:
                from_stock = Stock.objects.get(shop=from_shop, product=product)
                Stock.objects.create(
                    shop=to_shop,
                    product=product,
                    quantity=quantity,
                    average_cost=from_stock.average_cost,
                    selling_price=from_stock.selling_price
                )
            except Stock.DoesNotExist:
                Stock.objects.create(
                    shop=to_shop,
                    product=product,
                    quantity=quantity,
                    average_cost=Decimal('0.00'),
                    selling_price=Decimal('0.00')
                )


@receiver(post_delete, sender=StockTransferItem)
def update_stock_on_transfer_item_delete(sender, instance, **kwargs):
    """
    When a stock transfer item is deleted, reverse the stock changes.
    
    This function:
    1. Returns quantity to the source shop
    2. Reduces quantity from the destination shop
    """
    with transaction.atomic():
        product = instance.product
        quantity = instance.quantity
        from_shop = instance.stock_transfer.from_shop
        to_shop = instance.stock_transfer.to_shop
        
        # Return stock to source shop
        try:
            from_stock = Stock.objects.get(shop=from_shop, product=product)
            from_stock.quantity += quantity
            from_stock.save()
        except Stock.DoesNotExist:
            pass
            
        # Remove stock from destination shop
        try:
            to_stock = Stock.objects.get(shop=to_shop, product=product)
            to_stock.quantity -= quantity
            if to_stock.quantity < 0:
                to_stock.quantity = 0            
            to_stock.save()
        except Stock.DoesNotExist:
            pass