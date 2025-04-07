from decimal import Decimal
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.dispatch import receiver
from django.db import transaction
import logging

from inventory.models.inventory import Stock
from inventory.models.sales import SalesInvoice, SalesInvoiceItem

# Set up logger
logger = logging.getLogger(__name__)

@receiver(pre_save, sender=SalesInvoice)
def store_original_invoice_data(sender, instance, **kwargs):
    """
    Store the original shop and customer data before a SalesInvoice is updated.
    
    This allows proper handling of shop stock and customer credit changes.
    """
    if instance.pk:
        try:
            original = SalesInvoice.objects.get(pk=instance.pk)
            instance._original_shop = original.shop
            instance._original_customer = original.customer
            instance._original_total_amount = original.total_amount
            logger.debug(f"Stored original invoice data: shop={original.shop}, "
                         f"customer={original.customer}, total_amount={original.total_amount}")
        except SalesInvoice.DoesNotExist:
            logger.warning(f"Could not find original invoice with ID {instance.pk}")
            pass


@receiver(post_save, sender=SalesInvoice)
def handle_invoice_customer_change(sender, instance, created, **kwargs):
    """
    When a sales invoice's customer is changed, update customer credits.
    """
    if created:
        # For new invoices, update the customer credit
        if instance.customer:
            with transaction.atomic():
                due_amount = instance.total_amount - instance.paid_amount
                if isinstance(due_amount, float):
                    due_amount = Decimal(str(due_amount))
                instance.customer.credit += due_amount
                instance.customer.save(update_fields=['credit'])
                logger.info(f"Updated credit for new customer {instance.customer}: increased by {due_amount}")
        return
    
    # We only care about customer changes for existing invoices
    if not hasattr(instance, '_original_customer') or not hasattr(instance, '_original_total_amount'):
        return
        
    customer_changed = instance._original_customer != instance.customer
    amount_changed = instance._original_total_amount != instance.total_amount
    
    if not (customer_changed or amount_changed):
        return
    
    with transaction.atomic():
        # Handle customer change
        if customer_changed:
            # Calculate the unpaid amount
            due_amount = instance.total_amount - instance.paid_amount
            
            # Remove credit from original customer if exists
            if instance._original_customer:
                instance._original_customer.credit -= due_amount
                instance._original_customer.save(update_fields=['credit'])
                logger.info(f"Removed credit from original customer {instance._original_customer}: decreased by {due_amount}")
            
            # Add credit to new customer if exists
            if instance.customer:
                instance.customer.credit += due_amount
                instance.customer.save(update_fields=['credit'])
                logger.info(f"Added credit to new customer {instance.customer}: increased by {due_amount}")
        
        # Handle total amount change (without customer change)
        elif amount_changed and instance.customer:
            # Calculate the delta in total amount
            amount_delta = instance.total_amount - instance._original_total_amount
            
            # Update customer credit based on the delta
            instance.customer.credit += amount_delta
            instance.customer.save(update_fields=['credit'])
            logger.info(f"Adjusted credit for customer {instance.customer} due to amount change: {amount_delta}")


@receiver(pre_save, sender=SalesInvoiceItem)
def store_original_sales_item_data(sender, instance, **kwargs):
    """
    Store the original values before a SalesInvoiceItem is updated.
    
    This allows proper handling of stock quantities when item details change.
    """
    if instance.pk:
        try:
            original = SalesInvoiceItem.objects.get(pk=instance.pk)
            instance._original_quantity = original.quantity
            instance._original_product = original.product
            instance._original_invoice = original.sales_invoice
            instance._original_price = original.price
            logger.debug(f"Stored original sales item data: quantity={original.quantity}, "
                       f"product={original.product}, invoice={original.sales_invoice}, "
                       f"price={original.price}")
        except SalesInvoiceItem.DoesNotExist:
            logger.warning(f"Could not find original sales item with ID {instance.pk}")
            pass


@receiver(post_save, sender=SalesInvoiceItem)
def update_stock_on_sales_item_save(sender, instance, created, **kwargs):
    """
    Update stock quantities when a sales invoice item is created or updated.
    
    For new items:
    - Decrease quantity from the shop's stock
    - Validate sufficient stock exists
    
    For updated items:
    - Adjust quantities based on the quantity change
    - Handle product changes
    """
    shop = instance.sales_invoice.shop
    product = instance.product
    
    if created:
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
    else:
        # Handle updates to existing items
        if not hasattr(instance, '_original_quantity') or not hasattr(instance, '_original_price'):
            logger.warning(f"Missing original data for sales item {instance.pk}")
            return
        
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


@receiver(pre_delete, sender=SalesInvoiceItem)
def update_stock_on_sales_item_delete(sender, instance, **kwargs):
    """
    When a sales invoice item is deleted, return the stock to inventory.
    
    This function:
    1. Returns the quantity back to the shop's stock
    2. Updates the invoice total
    3. Updates customer credit
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
        
        # The invoice total will be updated in the post_delete signal
        

@receiver(post_delete, sender=SalesInvoiceItem)
def update_invoice_total_after_delete(sender, instance, **kwargs):
    """
    Update the invoice total after an item is deleted.
    """
    try:
        instance.sales_invoice.update_total_amount()
        logger.info(f"Updated total for invoice {instance.sales_invoice.id} after item deletion")
    except SalesInvoice.DoesNotExist:
        # Invoice might have been deleted as well
        logger.info("Could not update invoice total - invoice may have been deleted")
        pass


@receiver(post_save, sender=SalesInvoice)
def handle_invoice_shop_change(sender, instance, created, **kwargs):
    """
    When a sales invoice's shop is changed, update all associated items' stock.
    """
    if created:
        return  # New invoices are handled by the SalesInvoiceItem signals
    
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


@receiver(pre_delete, sender=SalesInvoice)
def handle_invoice_delete(sender, instance, **kwargs):
    """
    When a sales invoice is deleted, update customer credit.
    """
    with transaction.atomic():
        # Update customer credit if customer exists
        if instance.customer:
            due_amount = instance.total_amount - instance.paid_amount
            instance.customer.credit -= due_amount
            instance.customer.save(update_fields=['credit'])
            logger.info(f"Reduced credit for customer {instance.customer} by {due_amount} (invoice deleted)")