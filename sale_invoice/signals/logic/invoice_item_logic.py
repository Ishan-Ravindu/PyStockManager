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
            instance._original_discount_method = original.discount_method
            instance._original_discount_amount = original.discount_amount
            logger.debug(f"Stored original sales item data: quantity={original.quantity}, "
                       f"product={original.product}, invoice={original.sales_invoice}, "
                       f"price={original.price}, discount_method={original.discount_method}, "
                       f"discount_amount={original.discount_amount}")
        except instance.__class__.DoesNotExist:
            logger.warning(f"Could not find original sales item with ID {instance.pk}")
            pass


def calculate_item_total(quantity, price, discount_method=None, discount_amount=Decimal('0.00')):
    """
    Calculate the total amount for an invoice item considering discounts.
    
    Args:
        quantity: The quantity of the item
        price: The unit price of the item
        discount_method: The discount method ('amount' or 'percentage')
        discount_amount: The discount amount
        
    Returns:
        The total price after discount
    """
    if not price:
        return Decimal('0.00')
    
    unit_price = price
    
    if discount_method == 'amount':
        discounted_unit_price = max(unit_price - discount_amount, Decimal('0.00'))
    elif discount_method == 'percentage':
        discount_value = unit_price * (discount_amount / Decimal('100.00'))
        discounted_unit_price = max(unit_price - discount_value, Decimal('0.00'))
    else:
        discounted_unit_price = unit_price
    
    return quantity * discounted_unit_price


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
        
        # Get original invoice total before update
        original_total = instance.sales_invoice.total_amount
        
        # Update the invoice total
        instance.sales_invoice.update_total_amount()
        new_total = instance.sales_invoice.total_amount
        logger.info(f"Updated total for invoice {instance.sales_invoice.id} from {original_total} to {new_total}")
        
        # Update customer credit based on the change in invoice total
        if instance.sales_invoice.customer:
            # Calculate the change in invoice total
            total_change = new_total - original_total
            
            # Update the customer credit based on the total change
            instance.sales_invoice.customer.credit += total_change
            instance.sales_invoice.customer.save(update_fields=['credit'])
            logger.info(f"Adjusted credit for customer {instance.sales_invoice.customer} by {total_change}")


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
    
    with transaction.atomic():
        try:
            # Get original invoice total before update
            original_invoice_total = instance.sales_invoice.total_amount
            
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
                    # We'll handle customer credit after updating invoice totals
                    pass
            else:
                # Just a quantity or price change on the same product
                quantity_change = instance.quantity - instance._original_quantity
                
                if quantity_change != 0:
                    try:
                        stock = Stock.objects.get(shop=shop, product=product)
                        
                        # Only adjust stock by the difference in quantity
                        if quantity_change > 0:
                            # If quantity increased, check if there's enough stock
                            if stock.quantity < quantity_change:
                                logger.warning(f"Insufficient stock for additional quantity. "
                                            f"Available: {stock.quantity}, Additional: {quantity_change}")
                            
                            # Decrease stock by additional quantity
                            stock.quantity -= quantity_change
                            if stock.quantity < 0:
                                stock.quantity = 0
                            logger.info(f"Stock decreased by {quantity_change} for product {product} in shop {shop}")
                        else:
                            # If quantity decreased, return stock
                            stock.quantity -= quantity_change  # This is actually adding because quantity_change is negative
                            logger.info(f"Stock increased by {abs(quantity_change)} for product {product} in shop {shop}")
                        
                        stock.save()
                    except Stock.DoesNotExist:
                        logger.error(f"No stock record found for product {product} in shop {shop}")
            
            # Update the invoice totals
            if invoice_changed and instance._original_invoice:
                # Get original invoice's total before update
                original_old_invoice_total = instance._original_invoice.total_amount
                
                # Update original invoice total
                instance._original_invoice.update_total_amount()
                new_old_invoice_total = instance._original_invoice.total_amount
                logger.info(f"Updated total for original invoice {instance._original_invoice.id} from {original_old_invoice_total} to {new_old_invoice_total}")
                
                # Update original customer's credit if exists
                if instance._original_invoice.customer:
                    total_change = new_old_invoice_total - original_old_invoice_total
                    instance._original_invoice.customer.credit += total_change
                    instance._original_invoice.customer.save(update_fields=['credit'])
                    logger.info(f"Adjusted credit for original customer {instance._original_invoice.customer} by {total_change}")
            
            # Update current invoice total
            instance.sales_invoice.update_total_amount()
            new_invoice_total = instance.sales_invoice.total_amount
            logger.info(f"Updated total for invoice {instance.sales_invoice.id} from {original_invoice_total} to {new_invoice_total}")
            
            # Update customer credit based on invoice total change
            if instance.sales_invoice.customer:
                if invoice_changed:
                    # For invoice change, we need to calculate the new item's contribution to the total
                    item_total = calculate_item_total(
                        instance.quantity, 
                        instance.price, 
                        instance.discount_method, 
                        instance.discount_amount
                    )
                    instance.sales_invoice.customer.credit += item_total
                    instance.sales_invoice.customer.save(update_fields=['credit'])
                    logger.info(f"Added credit for new customer {instance.sales_invoice.customer} by {item_total}")
                else:
                    # For other changes, we adjust based on the change in invoice total
                    total_change = new_invoice_total - original_invoice_total
                    instance.sales_invoice.customer.credit += total_change
                    instance.sales_invoice.customer.save(update_fields=['credit'])
                    logger.info(f"Adjusted credit for customer {instance.sales_invoice.customer} by {total_change}")
                
        except Exception as e:
            logger.error(f"Error updating stock on sales item save: {str(e)}")
            raise


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
        
        # Get original invoice total before update
        original_invoice_total = instance.sales_invoice.total_amount
        
        # Calculate item total with discounts
        item_total = calculate_item_total(
            instance.quantity, 
            instance.price, 
            instance.discount_method, 
            instance.discount_amount
        )
        
        # Update customer credit if customer exists
        if instance.sales_invoice.customer:
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
        # Get original invoice total before update
        original_invoice_total = instance.sales_invoice.total_amount
        
        # Update the invoice total
        instance.sales_invoice.update_total_amount()
        new_invoice_total = instance.sales_invoice.total_amount
        
        logger.info(f"Updated total for invoice {instance.sales_invoice.id} from {original_invoice_total} to {new_invoice_total} after item deletion")
    except instance.sales_invoice.__class__.DoesNotExist:
        # Invoice might have been deleted as well
        logger.info("Could not update invoice total - invoice may have been deleted")
        pass