from decimal import Decimal
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.dispatch import receiver
from django.db import transaction
from django.core.exceptions import ValidationError
import logging

from inventory.models.inventory import Stock
from inventory.models.sales import SalesInvoice, SalesInvoiceItem

# Set up logger
logger = logging.getLogger(__name__)

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
        except SalesInvoiceItem.DoesNotExist:
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
    else:
        # Handle updates to existing items
        if not hasattr(instance, '_original_quantity'):
            return
        
        product_changed = (hasattr(instance, '_original_product') and 
                          instance._original_product != instance.product)
        
        invoice_changed = (hasattr(instance, '_original_invoice') and 
                          instance._original_invoice != instance.sales_invoice)
        
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
                else:
                    # Just a quantity change on the same product
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
            except Exception as e:
                logger.error(f"Error updating stock on sales item save: {str(e)}")
                raise
            
            # Update the invoice totals
            if invoice_changed and instance._original_invoice:
                instance._original_invoice.update_total_amount()
            instance.sales_invoice.update_total_amount()


@receiver(pre_delete, sender=SalesInvoiceItem)
def update_stock_on_sales_item_delete(sender, instance, **kwargs):
    """
    When a sales invoice item is deleted, return the stock to inventory.
    
    This function:
    1. Returns the quantity back to the shop's stock
    2. Updates the invoice total
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


@receiver(pre_save, sender=SalesInvoice)
def store_original_invoice_shop(sender, instance, **kwargs):
    """
    Store the original shop before a SalesInvoice is updated.
    """
    if instance.pk:
        try:
            original = SalesInvoice.objects.get(pk=instance.pk)
            instance._original_shop = original.shop
        except SalesInvoice.DoesNotExist:
            pass