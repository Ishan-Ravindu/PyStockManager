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
            logger.debug(f"Stored original shops for transfer {instance.pk}: "
                         f"from {original.from_shop} to {original.to_shop}")
        except StockTransfer.DoesNotExist:
            # Instance might have been deleted
            logger.warning(f"Could not find original transfer with ID {instance.pk}")
            pass


@receiver(post_save, sender=StockTransfer)
def handle_transfer_shop_changes(sender, instance, created, **kwargs):
    """
    When a stock transfer's shops are changed, update all associated items.
    
    This function:
    1. Reverses stock changes from the original shops
    2. Applies stock changes to the new shops
    3. Handles creation of new stock records when needed
    4. Updates average costs appropriately
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
        
    logger.info(f"Shops changed for transfer {instance.pk}: "
               f"from {instance._original_from_shop}->{instance._original_to_shop} "
               f"to {instance.from_shop}->{instance.to_shop}")
    
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
                
                logger.info(f"Returned {item.quantity} units to original source shop "
                           f"{instance._original_from_shop} for product {item.product}")
            except Stock.DoesNotExist:
                logger.warning(f"No stock record found in original source shop "
                              f"{instance._original_from_shop} for product {item.product}")
                pass
                
            # Remove stock from original destination shop with average cost adjustment
            try:
                original_to_stock = Stock.objects.get(
                    shop=instance._original_to_shop, 
                    product=item.product
                )
                
                # No need to adjust average cost when removing items in a transfer
                # Since the transfer doesn't involve buying at a different price
                original_to_stock.quantity -= item.quantity
                if original_to_stock.quantity < 0:
                    original_to_stock.quantity = 0
                    logger.warning(f"Prevented negative stock in original destination shop "
                                  f"{instance._original_to_shop} for product {item.product}")
                original_to_stock.save()
                
                logger.info(f"Removed {item.quantity} units from original destination shop "
                           f"{instance._original_to_shop} for product {item.product}")
            except Stock.DoesNotExist:
                logger.warning(f"No stock record found in original destination shop "
                              f"{instance._original_to_shop} for product {item.product}")
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
                    logger.warning(f"Prevented negative stock in new source shop "
                                  f"{instance.from_shop} for product {item.product}")
                new_from_stock.save()
                
                logger.info(f"Removed {item.quantity} units from new source shop "
                           f"{instance.from_shop} for product {item.product}")
            except Stock.DoesNotExist:
                logger.warning(f"No stock record found in new source shop "
                              f"{instance.from_shop} for product {item.product}")
                pass
                
            # Add stock to new destination shop with average cost calculation
            try:
                new_to_stock = Stock.objects.get(
                    shop=instance.to_shop, 
                    product=item.product
                )
                
                # For transfers, we need to properly handle average cost
                # The transferred items bring their average cost from the source shop
                try:
                    from_stock = Stock.objects.get(
                        shop=instance.from_shop, 
                        product=item.product
                    )
                    # Get the average cost from source shop
                    transfer_cost = from_stock.average_cost
                except Stock.DoesNotExist:
                    # If source stock doesn't exist, use destination's current average cost
                    transfer_cost = new_to_stock.average_cost
                    logger.warning(f"Using destination's average cost since source stock not found")
                
                # Calculate new average cost
                old_value = new_to_stock.average_cost * new_to_stock.quantity
                transfer_value = transfer_cost * item.quantity
                new_total_quantity = new_to_stock.quantity + item.quantity
                
                if new_total_quantity > 0:
                    new_to_stock.average_cost = (old_value + transfer_value) / new_total_quantity
                
                new_to_stock.quantity = new_total_quantity
                new_to_stock.save()
                
                logger.info(f"Added {item.quantity} units to new destination shop "
                           f"{instance.to_shop} for product {item.product} "
                           f"with average cost {new_to_stock.average_cost}")
            except Stock.DoesNotExist:
                # Create new stock record if doesn't exist in destination shop
                try:
                    new_from_stock = Stock.objects.get(
                        shop=instance.from_shop, 
                        product=item.product
                    )
                    # Create with source shop's average cost and selling price
                    Stock.objects.create(
                        shop=instance.to_shop,
                        product=item.product,
                        quantity=item.quantity,
                        average_cost=new_from_stock.average_cost,
                        selling_price=new_from_stock.selling_price
                    )
                    
                    logger.info(f"Created new stock record in destination shop "
                               f"{instance.to_shop} for product {item.product} "
                               f"with quantity {item.quantity} and average cost "
                               f"{new_from_stock.average_cost}")
                except Stock.DoesNotExist:
                    # Create with default values if source stock doesn't exist
                    Stock.objects.create(
                        shop=instance.to_shop,
                        product=item.product,
                        quantity=item.quantity,
                        average_cost=Decimal('0.00'),
                        selling_price=Decimal('0.00')
                    )
                    
                    logger.warning(f"Created new stock record with default values in destination shop "
                                  f"{instance.to_shop} for product {item.product}")


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
            logger.debug(f"Stored original transfer item data: "
                        f"quantity={original.quantity}, product={original.product}")
        except StockTransferItem.DoesNotExist:
            logger.warning(f"Could not find original transfer item with ID {instance.pk}")
            pass


@receiver(post_save, sender=StockTransferItem)
def update_stock_on_transfer_item_save(sender, instance, created, **kwargs):
    """
    Update stock quantities when a transfer item is created or updated.
    
    For new items:
    - Decrease quantity from source shop
    - Increase quantity in destination shop with appropriate average cost
    
    For updated items:
    - Adjust quantities based on the quantity change
    - Handle product changes
    - Update average costs
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
                        
                        # Add to destination with proper average cost
                        try:
                            to_stock = Stock.objects.get(
                                shop=instance.stock_transfer.to_shop, 
                                product=instance.product
                            )
                            
                            # Get source shop's average cost if available
                            try:
                                from_stock = Stock.objects.get(
                                    shop=instance.stock_transfer.from_shop, 
                                    product=instance.product
                                )
                                transfer_cost = from_stock.average_cost
                            except Stock.DoesNotExist:
                                # If no source stock, use destination's current cost
                                transfer_cost = to_stock.average_cost
                            
                            # Calculate new average cost
                            old_value = to_stock.average_cost * to_stock.quantity
                            transfer_value = transfer_cost * instance.quantity
                            new_total_quantity = to_stock.quantity + instance.quantity
                            
                            if new_total_quantity > 0:
                                to_stock.average_cost = (old_value + transfer_value) / new_total_quantity
                            
                            to_stock.quantity += instance.quantity
                            to_stock.save()
                            
                            logger.info(f"Added {instance.quantity} units of product {instance.product} "
                                       f"to shop {instance.stock_transfer.to_shop} with average cost "
                                       f"{to_stock.average_cost}")
                        except Stock.DoesNotExist:
                            # Create new stock record if it doesn't exist
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
                                           f"product {instance.product} with source shop's pricing")
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
                            
                            logger.info(f"Adjusted source shop stock by {-quantity_change} for "
                                       f"product {instance.product}")
                        except Stock.DoesNotExist:
                            logger.warning(f"No stock record exists for "
                                          f"shop {instance.stock_transfer.from_shop}, "
                                          f"product {instance.product}")
                            
                        # Update destination shop stock with proper average cost calculation
                        try:
                            to_stock = Stock.objects.get(
                                shop=instance.stock_transfer.to_shop, 
                                product=instance.product
                            )
                            
                            # Only recalculate average cost if adding more items
                            if quantity_change > 0:
                                # Get the average cost of transferred items
                                try:
                                    from_stock = Stock.objects.get(
                                        shop=instance.stock_transfer.from_shop, 
                                        product=instance.product
                                    )
                                    transfer_cost = from_stock.average_cost
                                except Stock.DoesNotExist:
                                    # Use destination's current cost if source not found
                                    transfer_cost = to_stock.average_cost
                                
                                # Calculate new average cost
                                old_value = to_stock.average_cost * to_stock.quantity
                                transfer_value = transfer_cost * quantity_change
                                new_total_quantity = to_stock.quantity + quantity_change
                                
                                if new_total_quantity > 0:
                                    to_stock.average_cost = (old_value + transfer_value) / new_total_quantity
                            elif quantity_change < 0:
                                # When removing items, we don't adjust average cost
                                # as we're just removing items at whatever cost they came in at
                                pass
                            
                            to_stock.quantity += quantity_change
                            to_stock.save()
                            
                            logger.info(f"Adjusted destination shop stock by {quantity_change} for "
                                       f"product {instance.product}, new average cost: {to_stock.average_cost}")
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
                                               f"product {instance.product} with source shop's pricing")
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
                    raise  # Re-raise the exception to ensure transaction rollback
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
            
            # Check if there's enough stock
            if from_stock.quantity < quantity:
                logger.warning(f"Insufficient stock for product {product} in shop {from_shop}. "
                             f"Available: {from_stock.quantity}, Requested: {quantity}")
            
            from_stock.quantity -= quantity
            if from_stock.quantity < 0:
                from_stock.quantity = 0
                logger.warning(f"Stock quantity set to zero for product {product} in shop {from_shop}")
            
            from_stock.save()
            
            logger.info(f"Reduced stock by {quantity} for product {product} in source shop {from_shop}")
        except Stock.DoesNotExist:
            logger.warning(f"No stock record exists for product {product} in source shop {from_shop}")
            
        # Increase stock in destination shop with average cost calculation
        try:
            to_stock = Stock.objects.get(shop=to_shop, product=product)
            
            # Get the average cost from source shop to calculate proper weighted average
            try:
                from_stock = Stock.objects.get(shop=from_shop, product=product)
                transfer_cost = from_stock.average_cost
            except Stock.DoesNotExist:
                # If source doesn't exist, use destination's current cost
                transfer_cost = to_stock.average_cost
                logger.warning(f"Using destination's current average cost since source stock not found")
            
            # Calculate new average cost using weighted average
            old_value = to_stock.average_cost * to_stock.quantity
            transfer_value = transfer_cost * quantity
            new_total_quantity = to_stock.quantity + quantity
            
            if new_total_quantity > 0:
                to_stock.average_cost = (old_value + transfer_value) / new_total_quantity
            
            to_stock.quantity += quantity
            to_stock.save()
            
            logger.info(f"Increased stock by {quantity} for product {product} in destination shop {to_shop} "
                       f"with average cost {to_stock.average_cost}")
        except Stock.DoesNotExist:
            # Create new stock record if doesn't exist in destination shop
            try:
                from_stock = Stock.objects.get(shop=from_shop, product=product)
                
                # Create with source shop's average cost and selling price
                Stock.objects.create(
                    shop=to_shop,
                    product=product,
                    quantity=quantity,
                    average_cost=from_stock.average_cost,
                    selling_price=from_stock.selling_price
                )
                
                logger.info(f"Created new stock record in destination shop {to_shop} for product {product} "
                           f"with quantity {quantity} and average cost {from_stock.average_cost}")
            except Stock.DoesNotExist:
                # Create with default values if source stock doesn't exist
                Stock.objects.create(
                    shop=to_shop,
                    product=product,
                    quantity=quantity,
                    average_cost=Decimal('0.00'),
                    selling_price=Decimal('0.00')
                )
                
                logger.warning(f"Created new stock record with default values in destination shop {to_shop} "
                              f"for product {product}")


@receiver(post_delete, sender=StockTransferItem)
def update_stock_on_transfer_item_delete(sender, instance, **kwargs):
    """
    When a stock transfer item is deleted, reverse the stock changes.
    
    This function:
    1. Returns quantity to the source shop
    2. Reduces quantity from the destination shop
    3. Maintains average costs appropriately
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
            
            logger.info(f"Returned {quantity} units to source shop {from_shop} for product {product} "
                       f"(transfer item deleted)")
        except Stock.DoesNotExist:
            # Create a new stock record if it doesn't exist
            Stock.objects.create(
                shop=from_shop,
                product=product,
                quantity=quantity,
                average_cost=Decimal('0.00'),
                selling_price=Decimal('0.00')
            )
            
            logger.warning(f"Created new stock record in source shop {from_shop} for product {product} "
                          f"with returned quantity {quantity} (transfer item deleted)")
            
        # Remove stock from destination shop
        try:
            to_stock = Stock.objects.get(shop=to_shop, product=product)
            
            # When removing items from a shop due to deletion, we don't adjust average cost
            # since we're just undoing a transfer which didn't involve buying at different prices
            
            to_stock.quantity -= quantity
            if to_stock.quantity < 0:
                logger.warning(f"Prevented negative stock for product {product} in shop {to_shop}")
                to_stock.quantity = 0            
            to_stock.save()
            
            logger.info(f"Removed {quantity} units from destination shop {to_shop} for product {product} "
                       f"(transfer item deleted)")
        except Stock.DoesNotExist:
            logger.warning(f"No stock record found for product {product} in destination shop {to_shop}")