from decimal import Decimal
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.db import transaction
from django.conf import settings
import logging

from inventory.models.stock import Stock
from purchase_invoice.models import PurchaseInvoice, PurchaseInvoiceItem
from entity.models import Supplier

# Set up logger
logger = logging.getLogger(__name__)

# Default markup percentage (can be moved to settings.py)
DEFAULT_MARKUP_PERCENTAGE = getattr(settings, 'DEFAULT_MARKUP_PERCENTAGE', Decimal('0.20'))


#########################################
# Purchase Invoice Stock Signal Handlers #
#########################################

@receiver(pre_save, sender=PurchaseInvoice)
def store_original_invoice_data(sender, instance, **kwargs):
    """
    Store the original shop and supplier values before a PurchaseInvoice is updated.
    
    This is necessary to correctly handle stock and payable adjustments when the invoice's
    shop or supplier is changed.
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


#############################################
# Purchase Invoice Supplier Payable Signals #
#############################################

@receiver(post_save, sender=PurchaseInvoice)
def update_supplier_payable_on_invoice_save(sender, instance, created, **kwargs):
    """
    Update supplier payable balance when a purchase invoice is created or updated.
    
    For new invoices:
    - Add total amount to supplier's payable balance
    
    For updated invoices:
    - Handle supplier changes or amount changes
    - Adjust payable balances accordingly
    """
    if not hasattr(instance, 'supplier') or instance.supplier is None:
        logger.warning(f"Invoice {instance.pk} has no supplier, skipping payable update")
        return

    with transaction.atomic():
        if created:
            # For new invoices, simply increase the supplier's payable balance
            try:
                supplier = instance.supplier
                # Convert to Decimal to ensure compatible types
                supplier.payable += Decimal(str(instance.total_amount))
                supplier.save()
                
                logger.info(f"Added {instance.total_amount} to supplier {supplier.pk} payable balance. "
                           f"New balance: {supplier.payable}")
            except Exception as e:
                logger.error(f"Error updating supplier payable on new invoice: {str(e)}")
                raise  # Re-raise to ensure transaction rollback
                
        else:
            # Handle updates to existing invoices
            if not hasattr(instance, '_original_supplier') or not hasattr(instance, '_original_total_amount'):
                logger.warning(f"Missing original data for invoice {instance.pk}, skipping payable update")
                return
                
            # Check if supplier changed
            supplier_changed = instance._original_supplier != instance.supplier
            
            # Check if total amount changed
            amount_changed = instance._original_total_amount != instance.total_amount
            
            if supplier_changed:
                # Need to remove amount from old supplier and add to new supplier
                try:
                    # Remove from old supplier
                    if instance._original_supplier:
                        old_supplier = instance._original_supplier
                        old_supplier.payable -= Decimal(str(instance._original_total_amount))
                        old_supplier.save()
                        
                        logger.info(f"Removed {instance._original_total_amount} from original supplier "
                                   f"{old_supplier.pk} payable. New balance: {old_supplier.payable}")
                    
                    # Add to new supplier
                    if instance.supplier:
                        new_supplier = instance.supplier
                        new_supplier.payable += Decimal(str(instance.total_amount))
                        new_supplier.save()
                        
                        logger.info(f"Added {instance.total_amount} to new supplier {new_supplier.pk} payable. "
                                   f"New balance: {new_supplier.payable}")
                               
                except Exception as e:
                    logger.error(f"Error updating supplier payable on supplier change: {str(e)}")
                    raise  # Re-raise to ensure transaction rollback
            
            elif amount_changed:
                # Just need to adjust the existing supplier's balance by the difference
                try:
                    supplier = instance.supplier
                    
                    # Calculate difference and adjust
                    amount_difference = Decimal(str(instance.total_amount)) - Decimal(str(instance._original_total_amount))
                    supplier.payable += amount_difference
                    supplier.save()
                    
                    logger.info(f"Adjusted supplier {supplier.pk} payable by {amount_difference}. "
                               f"New balance: {supplier.payable}")
                except Exception as e:
                    logger.error(f"Error updating supplier payable on amount change: {str(e)}")
                    raise  # Re-raise to ensure transaction rollback


@receiver(post_delete, sender=PurchaseInvoice)
def update_supplier_payable_on_invoice_delete(sender, instance, **kwargs):
    """
    When a purchase invoice is deleted, reduce the supplier's payable balance accordingly.
    """
    if not hasattr(instance, 'supplier') or instance.supplier is None:
        logger.warning(f"Deleted invoice had no supplier, skipping payable update")
        return
        
    supplier = instance.supplier
    
    with transaction.atomic():
        try:
            supplier.payable -= Decimal(str(instance.total_amount))
            supplier.save()
                
            logger.info(f"Reduced supplier {supplier.pk} payable by {instance.total_amount} due to invoice deletion. "
                       f"New balance: {supplier.payable}")
        except Exception as e:
            logger.error(f"Error updating supplier payable on invoice deletion: {str(e)}")
            raise  # Re-raise to ensure transaction rollback


###########################################
# Purchase Invoice Item Signal Handlers   #
###########################################

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
            
            logger.debug(f"Stored original purchase item data: "
                        f"quantity={original.quantity}, price={original.price}, "
                        f"product={original.product}, invoice={original.purchase_invoice}")
        except PurchaseInvoiceItem.DoesNotExist:
            logger.warning(f"Could not find original purchase item with ID {instance.pk}")
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
    - Prevent division by zero in calculations
    """
    shop = instance.purchase_invoice.shop
    product = instance.product
    
    # Validate price is positive
    if instance.price <= Decimal('0'):
        logger.warning(f"Non-positive price detected for PurchaseInvoiceItem {instance.pk}: {instance.price}")

    if created:
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
                else:
                    # If somehow we end up with zero quantity, keep the existing average cost
                    logger.warning(f"Attempted division by zero in average cost calculation for "
                                 f"product {product} at shop {shop}")
                
                stock.quantity = new_total_quantity
                stock.save()
                logger.info(f"Updated existing stock for product {product} at shop {shop}. "
                           f"New quantity: {new_total_quantity}, "
                           f"New average cost: {stock.average_cost}")
            except Stock.DoesNotExist:
                # Create with configurable markup
                new_stock = Stock.objects.create(
                    shop=shop,
                    product=product,
                    quantity=instance.quantity,
                    average_cost=instance.price,
                    selling_price=instance.price * (Decimal('1.0') + DEFAULT_MARKUP_PERCENTAGE)
                )
                logger.info(f"Created new stock record for product {product} at shop {shop}. "
                           f"Quantity: {new_stock.quantity}, "
                           f"Average cost: {new_stock.average_cost}, "
                           f"Selling price: {new_stock.selling_price}")
    else:
        # Handle updates to existing items
        if not hasattr(instance, '_original_quantity') or not hasattr(instance, '_original_price'):
            logger.warning(f"Missing original data for purchase item {instance.pk}")
            return
            
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
                            # If new_total_value <= 0, keep the current average_cost
                        
                        # Update the quantity
                        original_stock.quantity = new_quantity
                        if original_stock.quantity < 0:
                            original_stock.quantity = 0
                        
                        original_stock.save()
                        logger.info(f"Adjusted original stock for product change: "
                                   f"product {original_product}, shop {original_shop}, "
                                   f"removed {instance._original_quantity} units, "
                                   f"new avg cost: {original_stock.average_cost}")
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
                        
                        new_stock.quantity = new_total_quantity
                        new_stock.save()
                        
                        logger.info(f"Updated stock for new product/shop: "
                                   f"product {product}, shop {shop}, "
                                   f"added {instance.quantity} units, "
                                   f"new avg cost: {new_stock.average_cost}")
                    except Stock.DoesNotExist:
                        # Create with configurable markup
                        new_stock = Stock.objects.create(
                            shop=shop,
                            product=product,
                            quantity=instance.quantity,
                            average_cost=instance.price,
                            selling_price=instance.price * (Decimal('1.0') + DEFAULT_MARKUP_PERCENTAGE)
                        )
                        logger.info(f"Created new stock record for product {product} at shop {shop}")
                else:
                    # Just a quantity or price change on the same product/shop
                    try:
                        stock = Stock.objects.get(shop=shop, product=product)
                        
                        # Case 1: Only quantity changed
                        if quantity_change != 0 and not price_changed:
                            if quantity_change > 0:
                                # For additional quantity at the same price, straightforward calculation
                                old_value = stock.average_cost * stock.quantity
                                additional_value = instance.price * quantity_change
                                new_total_quantity = stock.quantity + quantity_change
                                
                                if new_total_quantity > 0:
                                    stock.average_cost = (old_value + additional_value) / new_total_quantity
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
                            
                            stock.quantity = new_total_quantity
                        
                        # Safety check to prevent negative quantities
                        if stock.quantity < 0:
                            stock.quantity = 0
                            logger.warning(f"Prevented negative stock for product {product} at shop {shop}")
                        
                        stock.save()
                        logger.info(f"Updated stock for product {product} at shop {shop}, "
                                   f"new quantity: {stock.quantity}, new avg cost: {stock.average_cost}")
                    except Stock.DoesNotExist:
                        logger.warning(f"No stock record found for product {product} at shop {shop}")
            except Exception as e:
                logger.error(f"Error updating stock on purchase item change: {str(e)}")
                raise  # Re-raise to ensure transaction rollback

    # Update the invoice total
    instance.purchase_invoice.update_total_amount()


@receiver(post_delete, sender=PurchaseInvoiceItem)
def update_stock_on_purchase_item_delete(sender, instance, **kwargs):
    """
    When a purchase invoice item is deleted, reverse the stock changes.
    
    This function:
    1. Reduces the stock quantity
    2. Updates the average cost
    3. Updates the invoice total
    """
    with transaction.atomic():
        shop = instance.purchase_invoice.shop
        product = instance.product
        
        try:
            stock = Stock.objects.get(shop=shop, product=product)
            
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
                # If new_total_value <= 0, keep the current average_cost
            
            # Update the quantity
            stock.quantity = new_quantity
            
            # Ensure quantity doesn't go below 0
            if stock.quantity < 0:
                stock.quantity = 0
                logger.warning(f"Prevented negative stock for product {product} at shop {shop}")
                
            stock.save()
            logger.info(f"Updated stock after item deletion: product {product}, shop {shop}, "
                       f"quantity: {stock.quantity}, avg cost: {stock.average_cost}")
        except Stock.DoesNotExist:
            logger.warning(f"No stock record found for product {product} at shop {shop}")
            
        # Update the invoice total
        try:
            instance.purchase_invoice.update_total_amount()
        except PurchaseInvoice.DoesNotExist:
            # Invoice might have been deleted as well
            logger.info("Could not update invoice total - invoice may have been deleted")