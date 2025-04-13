from decimal import Decimal
from django.db import transaction
from inventory.models.stock import Stock

def capture_original_sales_item_data(instance, logger):
    """
    Store the original values before a SalesInvoiceItem is updated.
    
    Args:
        instance: The SalesInvoiceItem instance being saved
        logger: Logger instance for recording operations
    """
    if instance.pk:
        try:
            original = instance.__class__.objects.get(pk=instance.pk)
            instance._original_quantity = original.quantity
            instance._original_product = original.product
            instance._original_invoice = original.sales_invoice
            instance._original_price = original.price
            logger.debug(f"Stored original sales item data: quantity={original.quantity}, "
                       f"product={original.product}, invoice={original.sales_invoice}, "
                       f"price={original.price}")
        except instance.__class__.DoesNotExist:
            logger.warning(f"Could not find original sales item with ID {instance.pk}")
            pass


def process_sales_item_creation(instance, logger):
    """
    Process a newly created sales invoice item.
    
    Args:
        instance: The new SalesInvoiceItem instance
        logger: Logger instance for recording operations
    """
    shop = instance.sales_invoice.shop
    product = instance.product
    
    # Handle new sales invoice items
    with transaction.atomic():
        try:
            stock = Stock.objects.get(shop=shop, product=product)
            
            # Check if there's enough stock
            if stock.quantity < instance.quantity:
                logger.warning(f"Insufficient stock for product {product} in shop {shop}. "
                             f"Available: {stock.quantity}, Requested: {instance.quantity}")
                # We'll still allow the sale but flag the warning
            
            # Reduce stock quantity
            stock.quantity -= instance.quantity
            if stock.quantity < 0:
                stock.quantity = 0
                logger.warning(f"Stock quantity set to zero for product {product} in shop {shop}")
            
            stock.save()
            logger.info(f"Stock reduced by {instance.quantity} for product {product} in shop {shop}")
        except Stock.DoesNotExist:
            logger.error(f"No stock record found for product {product} in shop {shop}")
            # Still allow the sale, but log the error
        
        # Update the invoice total
        instance.sales_invoice.update_total_amount()
        logger.info(f"Updated total for invoice {instance.sales_invoice.id}")
        
        # Update customer credit if customer exists
        if instance.sales_invoice.customer:
            item_total = instance.quantity * instance.price
            instance.sales_invoice.customer.credit += item_total
            instance.sales_invoice.customer.save(update_fields=['credit'])
            logger.info(f"Increased credit for customer {instance.sales_invoice.customer} by {item_total}")


def process_sales_item_update(instance, logger):
    """
    Process updates to a sales invoice item.
    
    Args:
        instance: The updated SalesInvoiceItem instance
        logger: Logger instance for recording operations
    """
    # Check for original data
    if not hasattr(instance, '_original_quantity') or not hasattr(instance, '_original_price'):
        logger.warning(f"Missing original data for sales item {instance.pk}")
        return
    
    shop = instance.sales_invoice.shop
    product = instance.product
    
    product_changed = (hasattr(instance, '_original_product') and 
                      instance._original_product != instance.product)
    
    invoice_changed = (hasattr(instance, '_original_invoice') and 
                      instance._original_invoice != instance.sales_invoice)
    
    # Calculate money changes for customer credit
    old_total = instance._original_quantity * instance._original_price
    new_total = instance.quantity * instance.price
    money_change = new_total - old_total
    
    with transaction.atomic():
        try:
            # If product or invoice changed, handle specially
            if product_changed or invoice_changed:
                # Return stock for the original product
                try:
                    original_shop = instance._original_invoice.shop
                    original_stock = Stock.objects.get(
                        shop=original_shop, 
                        product=instance._original_product
                    )
                    original_stock.quantity += instance._original_quantity
                    original_stock.save()
                    logger.info(f"Returned {instance._original_quantity} to stock for product "
                               f"{instance._original_product} in shop {original_shop}")
                except (Stock.DoesNotExist, AttributeError):
                    logger.warning(f"Could not return stock for original product "
                                  f"{getattr(instance, '_original_product', 'unknown')} "
                                  f"in shop {getattr(getattr(instance, '_original_invoice', None), 'shop', 'unknown')}")
                
                # Reduce stock for the new product/shop
                try:
                    new_stock = Stock.objects.get(shop=shop, product=product)
                    
                    # Check if there's enough stock
                    if new_stock.quantity < instance.quantity:
                        logger.warning(f"Insufficient stock for product {product} in shop {shop}. "
                                     f"Available: {new_stock.quantity}, Requested: {instance.quantity}")
                    
                    new_stock.quantity -= instance.quantity
                    if new_stock.quantity < 0:
                        new_stock.quantity = 0
                    new_stock.save()
                    logger.info(f"Stock reduced by {instance.quantity} for product {product} in shop {shop}")
                except Stock.DoesNotExist:
                    logger.error(f"No stock record found for product {product} in shop {shop}")
                
                # Handle customer credit changes if invoice changed
                if invoice_changed:
                    # Remove credit from original customer if exists
                    if instance._original_invoice.customer:
                        instance._original_invoice.customer.credit -= old_total
                        instance._original_invoice.customer.save(update_fields=['credit'])
                        logger.info(f"Reduced credit for original customer "
                                   f"{instance._original_invoice.customer} by {old_total}")
                    
                    # Add credit to new customer if exists
                    if instance.sales_invoice.customer:
                        instance.sales_invoice.customer.credit += new_total
                        instance.sales_invoice.customer.save(update_fields=['credit'])
                        logger.info(f"Increased credit for new customer "
                                   f"{instance.sales_invoice.customer} by {new_total}")
            else:
                # Just a quantity or price change on the same product
                quantity_change = instance.quantity - instance._original_quantity
                
                if quantity_change != 0:
                    try:
                        stock = Stock.objects.get(shop=shop, product=product)
                        
                        # If quantity increased, check if there's enough stock
                        if quantity_change > 0 and stock.quantity < quantity_change:
                            logger.warning(f"Insufficient stock for additional quantity. "
                                         f"Available: {stock.quantity}, Additional: {quantity_change}")
                        
                        # Adjust stock
                        stock.quantity -= quantity_change
                        if stock.quantity < 0:
                            stock.quantity = 0
                        stock.save()
                        logger.info(f"Stock adjusted by {-quantity_change} for product {product} in shop {shop}")
                    except Stock.DoesNotExist:
                        logger.error(f"No stock record found for product {product} in shop {shop}")
                
                # Update customer credit if money changed and customer exists
                if money_change != 0 and instance.sales_invoice.customer:
                    instance.sales_invoice.customer.credit += money_change
                    instance.sales_invoice.customer.save(update_fields=['credit'])
                    logger.info(f"Adjusted credit for customer {instance.sales_invoice.customer} by {money_change}")
        except Exception as e:
            logger.error(f"Error updating stock on sales item save: {str(e)}")
            raise
        
        # Update the invoice totals
        if invoice_changed and instance._original_invoice:
            instance._original_invoice.update_total_amount()
            logger.info(f"Updated total for original invoice {instance._original_invoice.id}")
        instance.sales_invoice.update_total_amount()
        logger.info(f"Updated total for invoice {instance.sales_invoice.id}")


def process_sales_item_deletion(instance, logger):
    """
    Process the deletion of a sales invoice item.
    
    Args:
        instance: The SalesInvoiceItem instance being deleted
        logger: Logger instance for recording operations
    """
    with transaction.atomic():
        shop = instance.sales_invoice.shop
        product = instance.product
        
        # Return stock when item is deleted
        try:
            stock = Stock.objects.get(shop=shop, product=product)
            stock.quantity += instance.quantity
            stock.save()
            logger.info(f"Returned {instance.quantity} to stock for product {product} in shop {shop} (item deleted)")
        except Stock.DoesNotExist:
            # Create a new stock record if it doesn't exist
            Stock.objects.create(
                shop=shop,
                product=product,
                quantity=instance.quantity,
                average_cost=Decimal('0.00'),
                selling_price=Decimal('0.00')
            )
            logger.warning(f"Created new stock record for product {product} in shop {shop} with returned quantity")
        
        # Update customer credit if customer exists
        if instance.sales_invoice.customer:
            item_total = instance.quantity * instance.price
            instance.sales_invoice.customer.credit -= item_total
            instance.sales_invoice.customer.save(update_fields=['credit'])
            logger.info(f"Reduced credit for customer {instance.sales_invoice.customer} by {item_total} (item deleted)")


def update_invoice_total_after_delete(instance, logger):
    """
    Update the invoice total after an item is deleted.
    
    Args:
        instance: The SalesInvoiceItem instance that was deleted
        logger: Logger instance for recording operations
    """
    try:
        instance.sales_invoice.update_total_amount()
        logger.info(f"Updated total for invoice {instance.sales_invoice.id} after item deletion")
    except instance.sales_invoice.__class__.DoesNotExist:
        # Invoice might have been deleted as well
        logger.info("Could not update invoice total - invoice may have been deleted")
        pass