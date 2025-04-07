from django.db.models.signals import pre_save, post_save, pre_delete
from django.dispatch import receiver
from django.db import transaction
import logging

from receipt.models import Receipt

# Set up logger
logger = logging.getLogger(__name__)

@receiver(pre_save, sender=Receipt)
def receipt_pre_save(sender, instance, **kwargs):
    """
    Capture the original state of a receipt before it's changed.
    
    This function saves the original amount, account, and sales_invoice 
    to enable proper handling of balance updates when these fields change.
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


@receiver(post_save, sender=Receipt)
def receipt_account_update(sender, instance, created, **kwargs):
    """
    Update account balance after receipt is saved.
    
    For new receipts, add the amount to the account balance.
    For updated receipts, handle account changes and amount changes appropriately.
    """
    if created:
        with transaction.atomic():
            instance.account.update_balance(
                amount=instance.amount,
                related_obj=instance,
                transaction_type='DEPOSIT',
                action_type='CREATE',
                description=f"Receipt #{instance.pk} for Sales Invoice #{instance.sales_invoice.pk}"
            )
            logger.info(f"Created new receipt #{instance.pk} for {instance.amount} to account {instance.account}")
    else:
        if hasattr(instance, '_original_amount') and hasattr(instance, '_original_account'):
            with transaction.atomic():
                if instance._original_account != instance.account:
                    # Account changed, reverse from old account and add to new account
                    instance._original_account.update_balance(
                        amount=-instance._original_amount,
                        related_obj=instance,
                        transaction_type='DEPOSIT',
                        action_type='UPDATE',
                        description=f"Reversal of Receipt #{instance.pk} (account changed)"
                    )
                    instance.account.update_balance(
                        amount=instance.amount,
                        related_obj=instance,
                        transaction_type='DEPOSIT',
                        action_type='UPDATE',
                        description=f"Receipt #{instance.pk} (updated to this account)"
                    )
                    logger.info(f"Receipt #{instance.pk} account changed from {instance._original_account} "
                               f"to {instance.account}, amount {instance.amount}")
                else:
                    # Same account but amount changed
                    delta = instance.amount - instance._original_amount
                    if delta != 0:
                        instance.account.update_balance(
                            amount=delta,
                            related_obj=instance,
                            transaction_type='DEPOSIT',
                            action_type='UPDATE',
                            description=f"Receipt #{instance.pk} amount changed from {instance._original_amount} to {instance.amount}"
                        )
                        logger.info(f"Receipt #{instance.pk} amount changed from {instance._original_amount} "
                                   f"to {instance.amount}, delta {delta}")


@receiver(post_save, sender=Receipt)
def receipt_invoice_customer_update(sender, instance, created, **kwargs):
    """
    Update sales invoice paid amount and customer credit.
    
    For new receipts, increase invoice paid amount and decrease customer credit.
    For updated receipts, handle invoice changes and amount changes appropriately.
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


@receiver(pre_delete, sender=Receipt)
def receipt_pre_delete(sender, instance, **kwargs):
    """
    When a receipt is deleted, reverse all the financial effects.
    
    This includes:
    1. Removing the amount from the account balance
    2. Decreasing the invoice paid amount
    3. Increasing the customer credit if applicable
    """
    with transaction.atomic():
        instance.account.update_balance(
            amount=-instance.amount,
            related_obj=instance,
            transaction_type='DEPOSIT',
            action_type='DELETE',
            description=f"Deletion of Receipt #{instance.pk} for Sales Invoice #{instance.sales_invoice.pk}"
        )
        logger.info(f"Receipt #{instance.pk} deleted, removed {instance.amount} from account {instance.account}")
        
        instance.sales_invoice.paid_amount -= instance.amount
        instance.sales_invoice.save(update_fields=['paid_amount'])
        logger.info(f"Reduced paid amount for sales invoice #{instance.sales_invoice.pk} by {instance.amount}")
        
        if instance.sales_invoice.customer:
            instance.sales_invoice.customer.credit += instance.amount
            instance.sales_invoice.customer.save(update_fields=['credit'])
            logger.info(f"Increased credit for customer {instance.sales_invoice.customer} by {instance.amount}")