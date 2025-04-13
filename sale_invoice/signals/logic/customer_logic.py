from decimal import Decimal
from django.db import transaction

def capture_original_invoice_data(instance, logger):
    """
    Store the original shop and customer data before a SalesInvoice is updated.
    
    Args:
        instance: The SalesInvoice instance being saved
        logger: Logger instance for recording operations
    """
    if instance.pk:
        try:
            original = instance.__class__.objects.get(pk=instance.pk)
            instance._original_shop = original.shop
            instance._original_customer = original.customer
            instance._original_total_amount = original.total_amount
            logger.debug(f"Stored original invoice data: shop={original.shop}, "
                         f"customer={original.customer}, total_amount={original.total_amount}")
        except instance.__class__.DoesNotExist:
            logger.warning(f"Could not find original invoice with ID {instance.pk}")
            pass


def process_invoice_customer_change(instance, created, logger):
    """
    Process customer changes on a sales invoice.
    
    Args:
        instance: The SalesInvoice instance that was saved
        created: Boolean indicating if this is a new instance
        logger: Logger instance for recording operations
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


def handle_invoice_deletion(instance, logger):
    """
    Process the deletion of a sales invoice.
    
    Args:
        instance: The SalesInvoice instance being deleted
        logger: Logger instance for recording operations
    """
    with transaction.atomic():
        # Update customer credit if customer exists
        if instance.customer:
            due_amount = instance.total_amount - instance.paid_amount
            instance.customer.credit -= due_amount
            instance.customer.save(update_fields=['credit'])
            logger.info(f"Reduced credit for customer {instance.customer} by {due_amount} (invoice deleted)")