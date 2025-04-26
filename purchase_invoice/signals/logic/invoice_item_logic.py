from decimal import Decimal
from django.db import transaction
from django.conf import settings

from inventory.models.stock import Stock

# Default markup percentage (can be moved to settings.py)
DEFAULT_MARKUP_PERCENTAGE = 0

def update_selling_price(stock, logger):
    """
    Update the selling price based on the product's profit margin.
    If profit margin is not set, use 0.
    
    Args:
        stock: The Stock instance
        logger: Logger instance for recording operations
    """
    try:
        # Update selling price based on the product's profit margin
        # Convert percentage (like 30%) to decimal (0.3) for calculation
        profit_margin_decimal = stock.product.profit_margin / 100
        stock.selling_price = stock.average_cost * (Decimal('1.0') + profit_margin_decimal)
        logger.info(f"Updated selling price for product {stock.product} to {stock.selling_price} "
                   f"based on profit margin {stock.product.profit_margin}%")
    except AttributeError:
        # Use 0 as profit margin if product doesn't have profit_margin
        stock.selling_price = stock.average_cost
        logger.info(f"Updated selling price for product {stock.product} to {stock.selling_price} "
                   f"using zero markup as profit margin is not set")

def capture_original_item_data(instance, logger):
    """
    Store the original values before a PurchaseInvoiceItem is updated.
    
    Args:
        instance: The PurchaseInvoiceItem instance being saved
        logger: Logger instance for recording operations
    """
    if instance.pk:
        try:
            original = instance.__class__.objects.get(pk=instance.pk)
            
            # Store all relevant original values
            instance._original_quantity = original.quantity
            instance._original_price = original.price
            instance._original_product = original.product
            instance._original_invoice = original.purchase_invoice
            
            logger.debug(f"Stored original purchase item data: "
                        f"quantity={original.quantity}, price={original.price}, "
                        f"product={original.product}, invoice={original.purchase_invoice}")
        except instance.__class__.DoesNotExist:
            logger.warning(f"Could not find original purchase item with ID {instance.pk}")
            pass


def process_purchase_item_creation(instance, logger):
    """
    Process a newly created purchase invoice item.
    
    Args:
        instance: The new PurchaseInvoiceItem instance
        logger: Logger instance for recording operations
    """
    shop = instance.purchase_invoice.shop
    product = instance.product
    
    # Validate price is positive
    if instance.price <= Decimal('0'):
        logger.warning(f"Non-positive price detected for PurchaseInvoiceItem {instance.pk}: {instance.price}")

    # Handle new items
    logger.info(f"Creating new purchase invoice item for product {product} at shop {shop}")
    with transaction.atomic():
        try:
            stock = Stock.objects.get(shop=shop, product=product)
            
            # Update quantity and recalculate average cost
            old_value = stock.average_cost * stock.quantity
            new_value = instance.price * instance.quantity
            new_total_quantity = stock.quantity + instance.quantity
            
            # Prevent division by zero
            if new_total_quantity > 0:
                stock.average_cost = (old_value + new_value) / new_total_quantity
                # Update selling price when average cost changes
                update_selling_price(stock, logger)
            else:
                # If somehow we end up with zero quantity, keep the existing average cost
                logger.warning(f"Attempted division by zero in average cost calculation for "
                             f"product {product} at shop {shop}")
            
            stock.quantity = new_total_quantity
            stock.save()
            logger.info(f"Updated existing stock for product {product} at shop {shop}. "
                       f"New quantity: {new_total_quantity}, "
                       f"New average cost: {stock.average_cost}, "
                       f"New selling price: {stock.selling_price}")
        except Stock.DoesNotExist:
            # Create new stock with selling price based on profit margin
            try:
                # Try to use product's profit margin
                profit_margin = product.profit_margin
                selling_price = instance.price * (Decimal('1.0') + profit_margin)
                logger.info(f"Using product's profit margin {profit_margin} for new stock")
            except AttributeError:
                # Fallback to default markup
                profit_margin = DEFAULT_MARKUP_PERCENTAGE
                selling_price = instance.price * (Decimal('1.0') + DEFAULT_MARKUP_PERCENTAGE)
                logger.info(f"Using default markup {DEFAULT_MARKUP_PERCENTAGE} for new stock")
                
            new_stock = Stock.objects.create(
                shop=shop,
                product=product,
                quantity=instance.quantity,
                average_cost=instance.price,
                selling_price=selling_price
            )
            logger.info(f"Created new stock record for product {product} at shop {shop}. "
                       f"Quantity: {new_stock.quantity}, "
                       f"Average cost: {new_stock.average_cost}, "
                       f"Selling price: {new_stock.selling_price}")

    # Update the invoice total
    instance.purchase_invoice.update_total_amount()


def process_purchase_item_update(instance, logger):
    """
    Process changes when a purchase invoice item is updated.
    
    Args:
        instance: The updated PurchaseInvoiceItem instance
        logger: Logger instance for recording operations
    """
    # Check for original data
    if not hasattr(instance, '_original_quantity') or not hasattr(instance, '_original_price'):
        logger.warning(f"Missing original data for purchase item {instance.pk}")
        return
        
    shop = instance.purchase_invoice.shop
    product = instance.product
        
    # Check if the invoice changed
    invoice_changed = (hasattr(instance, '_original_invoice') and 
                      instance._original_invoice != instance.purchase_invoice)
    
    # Check if the product changed
    product_changed = (hasattr(instance, '_original_product') and 
                      instance._original_product != instance.product)
    
    # Calculate changes
    quantity_change = instance.quantity - instance._original_quantity
    price_changed = instance.price != instance._original_price
    
    with transaction.atomic():
        try:
            # If invoice or product changed, handle specially
            if invoice_changed or product_changed:
                logger.info(f"Product or invoice changed for purchase item {instance.pk}")
                # First, revert the original item effects
                try:
                    original_shop = instance._original_invoice.shop
                    original_product = instance._original_product
                    
                    original_stock = Stock.objects.get(
                        shop=original_shop, 
                        product=original_product
                    )
                    
                    # Calculate the value that needs to be removed
                    original_item_value = instance._original_price * instance._original_quantity
                    original_total_value = original_stock.average_cost * original_stock.quantity
                    
                    # Adjust for the removed item
                    new_quantity = original_stock.quantity - instance._original_quantity
                    
                    # Calculate new average cost if quantity will still be positive
                    if new_quantity > 0:
                        # When removing value, we need to be careful with the calculation
                        # to avoid distorting the average cost
                        new_total_value = original_total_value - original_item_value
                        
                        # Only update average cost if the math works out
                        if new_total_value > 0:
                            original_stock.average_cost = new_total_value / new_quantity
                            # Update selling price when average cost changes
                            update_selling_price(original_stock, logger)
                        # If new_total_value <= 0, keep the current average_cost
                    
                    # Update the quantity
                    original_stock.quantity = new_quantity
                    if original_stock.quantity < 0:
                        original_stock.quantity = 0
                    
                    original_stock.save()
                    logger.info(f"Adjusted original stock for product change: "
                               f"product {original_product}, shop {original_shop}, "
                               f"removed {instance._original_quantity} units, "
                               f"new avg cost: {original_stock.average_cost}, "
                               f"new selling price: {original_stock.selling_price}")
                except (Stock.DoesNotExist, AttributeError) as e:
                    logger.warning(f"Error adjusting original stock: {str(e)}")
                
                # Then add the new item effects
                try:
                    new_stock = Stock.objects.get(shop=shop, product=product)
                    
                    # Update quantity and recalculate average cost
                    old_value = new_stock.average_cost * new_stock.quantity
                    new_value = instance.price * instance.quantity
                    new_total_quantity = new_stock.quantity + instance.quantity
                    
                    if new_total_quantity > 0:
                        new_stock.average_cost = (old_value + new_value) / new_total_quantity
                        # Update selling price when average cost changes
                        update_selling_price(new_stock, logger)
                    
                    new_stock.quantity = new_total_quantity
                    new_stock.save()
                    
                    logger.info(f"Updated stock for new product/shop: "
                               f"product {product}, shop {shop}, "
                               f"added {instance.quantity} units, "
                               f"new avg cost: {new_stock.average_cost}, "
                               f"new selling price: {new_stock.selling_price}")
                except Stock.DoesNotExist:
                    # Create with selling price based on profit margin
                    try:
                        # Try to use product's profit margin
                        profit_margin = product.profit_margin
                        selling_price = instance.price * (Decimal('1.0') + profit_margin)
                        logger.info(f"Using product's profit margin {profit_margin} for new stock")
                    except AttributeError:
                        # Fallback to default markup
                        profit_margin = DEFAULT_MARKUP_PERCENTAGE
                        selling_price = instance.price * (Decimal('1.0') + DEFAULT_MARKUP_PERCENTAGE)
                        logger.info(f"Using default markup {DEFAULT_MARKUP_PERCENTAGE} for new stock")
                    
                    new_stock = Stock.objects.create(
                        shop=shop,
                        product=product,
                        quantity=instance.quantity,
                        average_cost=instance.price,
                        selling_price=selling_price
                    )
                    logger.info(f"Created new stock record for product {product} at shop {shop}, "
                               f"selling price: {new_stock.selling_price}")
            else:
                # Just a quantity or price change on the same product/shop
                try:
                    stock = Stock.objects.get(shop=shop, product=product)
                    average_cost_changed = False
                    
                    # Case 1: Only quantity changed
                    if quantity_change != 0 and not price_changed:
                        if quantity_change > 0:
                            # For additional quantity at the same price, straightforward calculation
                            old_value = stock.average_cost * stock.quantity
                            additional_value = instance.price * quantity_change
                            new_total_quantity = stock.quantity + quantity_change
                            
                            if new_total_quantity > 0:
                                stock.average_cost = (old_value + additional_value) / new_total_quantity
                                average_cost_changed = True
                        else:
                            # For reduced quantity, we need to be careful
                            # If the price at which units were "removed" is different from
                            # the average cost, this changes the average cost of remaining units
                            old_value = stock.average_cost * stock.quantity
                            removed_value = instance.price * abs(quantity_change)
                            new_total_quantity = stock.quantity + quantity_change  # quantity_change is negative
                            
                            if new_total_quantity > 0:
                                # Only adjust avg cost if the price differs from avg cost
                                if instance.price != stock.average_cost:
                                    new_total_value = old_value - removed_value
                                    stock.average_cost = new_total_value / new_total_quantity
                                    average_cost_changed = True
                        
                        stock.quantity = new_total_quantity
                        
                    # Case 2: Only price changed
                    elif price_changed and quantity_change == 0:
                        # Recalculate by removing old value and adding new value
                        old_item_value = instance._original_price * instance.quantity
                        new_item_value = instance.price * instance.quantity
                        
                        old_total_value = stock.average_cost * stock.quantity
                        # Remove contribution of old price, add contribution of new price
                        adjusted_value = old_total_value - old_item_value + new_item_value
                        
                        if stock.quantity > 0:
                            stock.average_cost = adjusted_value / stock.quantity
                            average_cost_changed = True
                    
                    # Case 3: Both price and quantity changed
                    elif price_changed and quantity_change != 0:
                        # This is the most complex case
                        # First, remove the old item completely
                        old_total_value = stock.average_cost * stock.quantity
                        old_item_value = instance._original_price * instance._original_quantity
                        
                        # Then add the new item
                        new_item_value = instance.price * instance.quantity
                        
                        # Calculate the adjusted total and quantity
                        adjusted_value = old_total_value - old_item_value + new_item_value
                        new_total_quantity = stock.quantity - instance._original_quantity + instance.quantity
                        
                        if new_total_quantity > 0:
                            stock.average_cost = adjusted_value / new_total_quantity
                            average_cost_changed = True
                        
                        stock.quantity = new_total_quantity
                    
                    # Update selling price if average cost changed
                    if average_cost_changed:
                        update_selling_price(stock, logger)
                    
                    # Safety check to prevent negative quantities
                    if stock.quantity < 0:
                        stock.quantity = 0
                        logger.warning(f"Prevented negative stock for product {product} at shop {shop}")
                    
                    stock.save()
                    logger.info(f"Updated stock for product {product} at shop {shop}, "
                               f"new quantity: {stock.quantity}, new avg cost: {stock.average_cost}, "
                               f"new selling price: {stock.selling_price}")
                except Stock.DoesNotExist:
                    logger.warning(f"No stock record found for product {product} at shop {shop}")
        except Exception as e:
            logger.error(f"Error updating stock on purchase item change: {str(e)}")
            raise  # Re-raise to ensure transaction rollback

    # Update the invoice total
    instance.purchase_invoice.update_total_amount()


def process_purchase_item_deletion(instance, logger):
    """
    Process the deletion of a purchase invoice item.
    
    Args:
        instance: The PurchaseInvoiceItem instance being deleted
        logger: Logger instance for recording operations
    """
    with transaction.atomic():
        shop = instance.purchase_invoice.shop
        product = instance.product
        
        try:
            stock = Stock.objects.get(shop=shop, product=product)
            average_cost_changed = False
            
            # Calculate the value that needs to be removed
            item_value = instance.price * instance.quantity
            total_value = stock.average_cost * stock.quantity
            
            # Calculate new quantity
            new_quantity = stock.quantity - instance.quantity
            
            # Update the average cost if quantity will still be positive
            if new_quantity > 0:
                # When removing value, we need a careful calculation
                new_total_value = total_value - item_value
                
                # Only update average cost if the math works out
                if new_total_value > 0:
                    stock.average_cost = new_total_value / new_quantity
                    average_cost_changed = True
                # If new_total_value <= 0, keep the current average_cost
            
            # Update the quantity
            stock.quantity = new_quantity
            
            # Update selling price if average cost changed
            if average_cost_changed:
                update_selling_price(stock, logger)
            
            # Ensure quantity doesn't go below 0
            if stock.quantity < 0:
                stock.quantity = 0
                logger.warning(f"Prevented negative stock for product {product} at shop {shop}")
                
            stock.save()
            logger.info(f"Updated stock after item deletion: product {product}, shop {shop}, "
                       f"quantity: {stock.quantity}, avg cost: {stock.average_cost}, "
                       f"selling price: {stock.selling_price}")
        except Stock.DoesNotExist:
            logger.warning(f"No stock record found for product {product} at shop {shop}")
            
        # Update the invoice total
        try:
            instance.purchase_invoice.update_total_amount()
        except instance.purchase_invoice.__class__.DoesNotExist:
            # Invoice might have been deleted as well
            logger.info("Could not update invoice total - invoice may have been deleted")