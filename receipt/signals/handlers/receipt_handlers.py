from django.db import transaction

from receipt.models import Receipt


def capture_original_receipt_state(instance, logger):
    """
    Capture the original state of a receipt before it's changed.
    
    Args:
        instance: The Receipt instance being saved
        logger: Logger instance for recording operations
    """
    if instance.pk:
        try:
            old_receipt = Receipt.objects.get(pk=instance.pk)
            instance._original_amount = old_receipt.amount
            instance._original_account = old_receipt.account
            instance._original_sales_invoice = old_receipt.sales_invoice
            logger.debug(f"Saved original receipt state: amount={old_receipt.amount}, "
                       f"account={old_receipt.account}, invoice={old_receipt.sales_invoice}")
        except Receipt.DoesNotExist:
            # New instance or instance was deleted
            instance._original_amount = None
            instance._original_account = None
            instance._original_sales_invoice = None
            logger.warning(f"Couldn't find original receipt with ID {instance.pk}")


def update_account_balance(instance, created, logger):
    """
    Update account balance after receipt is saved.
    
    Args:
        instance: The Receipt instance that was saved
        created: Boolean indicating if this is a new instance
        logger: Logger instance for recording operations
    """
    if created:
        with transaction.atomic():
            instance.account.balance += instance.amount
            instance.account.save(update_fields=['balance'])
            logger.info(f"Created new receipt #{instance.pk} for {instance.amount} to account {instance.account}")
    else:
        if hasattr(instance, '_original_amount') and hasattr(instance, '_original_account'):
            with transaction.atomic():
                if instance._original_account != instance.account:
                    # Account changed, reverse from old account and add to new account
                    instance._original_account.balance -= instance._original_amount
                    instance._original_account.save(update_fields=['balance'])
                    
                    instance.account.balance += instance.amount
                    instance.account.save(update_fields=['balance'])
                    logger.info(f"Receipt #{instance.pk} account changed from {instance._original_account} "
                               f"to {instance.account}, amount {instance.amount}")
                else:
                    # Same account but amount changed
                    delta = instance.amount - instance._original_amount
                    if delta != 0:
                        instance.account.balance += delta
                        instance.account.save(update_fields=['balance'])
                        logger.info(f"Receipt #{instance.pk} amount changed from {instance._original_amount} "
                                   f"to {instance.amount}, delta {delta}")


def update_invoice_customer(instance, created, logger):
    """
    Update sales invoice paid amount and customer credit.
    
    Args:
        instance: The Receipt instance that was saved
        created: Boolean indicating if this is a new instance
        logger: Logger instance for recording operations
    """
    if created:
        with transaction.atomic():
            instance.sales_invoice.paid_amount += instance.amount
            instance.sales_invoice.save(update_fields=['paid_amount'])
            logger.info(f"Updated sales invoice #{instance.sales_invoice.pk} paid amount "
                       f"increased by {instance.amount}")
            
            if instance.sales_invoice.customer:
                instance.sales_invoice.customer.credit -= instance.amount
                instance.sales_invoice.customer.save(update_fields=['credit'])
                logger.info(f"Updated customer {instance.sales_invoice.customer} credit "
                           f"decreased by {instance.amount}")
    else:
        if hasattr(instance, '_original_amount') and hasattr(instance, '_original_sales_invoice'):
            with transaction.atomic():
                if instance._original_sales_invoice != instance.sales_invoice:
                    # Invoice changed, reverse changes on old invoice and apply to new invoice
                    instance._original_sales_invoice.paid_amount -= instance._original_amount
                    instance._original_sales_invoice.save(update_fields=['paid_amount'])
                    logger.info(f"Original invoice #{instance._original_sales_invoice.pk} paid amount "
                               f"decreased by {instance._original_amount}")
                    
                    if instance._original_sales_invoice.customer:
                        instance._original_sales_invoice.customer.credit += instance._original_amount
                        instance._original_sales_invoice.customer.save(update_fields=['credit'])
                        logger.info(f"Original customer {instance._original_sales_invoice.customer} credit "
                                   f"increased by {instance._original_amount}")
                    
                    instance.sales_invoice.paid_amount += instance.amount
                    instance.sales_invoice.save(update_fields=['paid_amount'])
                    logger.info(f"New invoice #{instance.sales_invoice.pk} paid amount "
                               f"increased by {instance.amount}")
                    
                    if instance.sales_invoice.customer:
                        instance.sales_invoice.customer.credit -= instance.amount
                        instance.sales_invoice.customer.save(update_fields=['credit'])
                        logger.info(f"New customer {instance.sales_invoice.customer} credit "
                                   f"decreased by {instance.amount}")
                else:
                    # Same invoice but amount changed
                    delta = instance.amount - instance._original_amount
                    if delta != 0:
                        instance.sales_invoice.paid_amount += delta
                        instance.sales_invoice.save(update_fields=['paid_amount'])
                        logger.info(f"Invoice #{instance.sales_invoice.pk} paid amount "
                                   f"adjusted by {delta}")
                        
                        if instance.sales_invoice.customer:
                            instance.sales_invoice.customer.credit -= delta
                            instance.sales_invoice.customer.save(update_fields=['credit'])
                            logger.info(f"Customer {instance.sales_invoice.customer} credit "
                                       f"adjusted by -{delta}")


def reverse_receipt_effects(instance, logger):
    """
    Reverse all financial effects of a receipt when it's deleted.
    
    Args:
        instance: The Receipt instance being deleted
        logger: Logger instance for recording operations
    """
    with transaction.atomic():
        instance.account.balance -= instance.amount
        instance.account.save(update_fields=['balance'])
        logger.info(f"Receipt #{instance.pk} deleted, removed {instance.amount} from account {instance.account}")
        
        instance.sales_invoice.paid_amount -= instance.amount
        instance.sales_invoice.save(update_fields=['paid_amount'])
        logger.info(f"Reduced paid amount for sales invoice #{instance.sales_invoice.pk} by {instance.amount}")
        
        if instance.sales_invoice.customer:
            instance.sales_invoice.customer.credit += instance.amount
            instance.sales_invoice.customer.save(update_fields=['credit'])
            logger.info(f"Increased credit for customer {instance.sales_invoice.customer} by {instance.amount}")