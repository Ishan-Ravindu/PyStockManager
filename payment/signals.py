from django.db.models.signals import pre_save, post_save, pre_delete
from django.dispatch import receiver
from django.db import transaction
from decimal import Decimal
import logging

from payment.models import Payment

# Set up logger
logger = logging.getLogger(__name__)

@receiver(pre_save, sender=Payment)
def payment_pre_save(sender, instance, **kwargs):
    """
    Capture the original state of a payment before it's changed.
    
    This function saves the original amount, account, and purchase_invoice 
    to enable proper handling of balance updates when these fields change.
    """
    if instance.pk:
        try:
            old_payment = Payment.objects.get(pk=instance.pk)
            instance._original_amount = old_payment.amount
            instance._original_account = old_payment.account
            instance._original_purchase_invoice = old_payment.purchase_invoice
            logger.debug(f"Saved original payment state: amount={old_payment.amount}, "
                       f"account={old_payment.account}, invoice={old_payment.purchase_invoice}")
        except Payment.DoesNotExist:
            # New instance or instance was deleted
            instance._original_amount = None
            instance._original_account = None
            instance._original_purchase_invoice = None
            logger.warning(f"Couldn't find original payment with ID {instance.pk}")


@receiver(post_save, sender=Payment)
def payment_account_update(sender, instance, created, **kwargs):
    """
    Update account balance after payment is saved.
    
    For new payments, subtract the amount from the account balance.
    For updated payments, handle account changes and amount changes appropriately.
    """
    if created:
        with transaction.atomic():
            instance.account.balance -= instance.amount
            instance.account.save(update_fields=['balance'])
            logger.info(f"Created new payment #{instance.pk} for {instance.amount} from account {instance.account}")
    else:
        if hasattr(instance, '_original_amount') and hasattr(instance, '_original_account'):
            with transaction.atomic():
                if instance._original_account != instance.account:
                    # Account changed, reverse from old account and subtract from new account
                    instance._original_account.balance += instance._original_amount
                    instance._original_account.save(update_fields=['balance'])
                    
                    instance.account.balance -= instance.amount
                    instance.account.save(update_fields=['balance'])
                    logger.info(f"Payment #{instance.pk} account changed from {instance._original_account} "
                               f"to {instance.account}, amount {instance.amount}")
                else:
                    # Same account but amount changed
                    delta = instance.amount - instance._original_amount
                    if delta != 0:
                        instance.account.balance -= delta
                        instance.account.save(update_fields=['balance'])
                        logger.info(f"Payment #{instance.pk} amount changed from {instance._original_amount} "
                                   f"to {instance.amount}, delta {delta}")


@receiver(post_save, sender=Payment)
def payment_invoice_supplier_update(sender, instance, created, **kwargs):
    """
    Update purchase invoice paid amount and supplier payable.
    
    For new payments, increase invoice paid amount and decrease supplier payable.
    For updated payments, handle invoice changes and amount changes appropriately.
    """
    if created:
        with transaction.atomic():
            instance.purchase_invoice.paid_amount += instance.amount
            instance.purchase_invoice.save(update_fields=['paid_amount'])
            logger.info(f"Updated purchase invoice #{instance.purchase_invoice.pk} paid amount "
                       f"increased by {instance.amount}")
            
            if instance.purchase_invoice.supplier:
                instance.purchase_invoice.supplier.payable -= Decimal(str(instance.amount))
                instance.purchase_invoice.supplier.save(update_fields=['payable'])
                logger.info(f"Updated supplier {instance.purchase_invoice.supplier} payable "
                           f"decreased by {instance.amount}")
    else:
        if hasattr(instance, '_original_amount') and hasattr(instance, '_original_purchase_invoice'):
            with transaction.atomic():
                if instance._original_purchase_invoice != instance.purchase_invoice:
                    # Invoice changed, reverse changes on old invoice and apply to new invoice
                    instance._original_purchase_invoice.paid_amount -= instance._original_amount
                    instance._original_purchase_invoice.save(update_fields=['paid_amount'])
                    logger.info(f"Original invoice #{instance._original_purchase_invoice.pk} paid amount "
                               f"decreased by {instance._original_amount}")
                    
                    if instance._original_purchase_invoice.supplier:
                        instance._original_purchase_invoice.supplier.payable += Decimal(str(instance._original_amount))
                        instance._original_purchase_invoice.supplier.save(update_fields=['payable'])
                        logger.info(f"Original supplier {instance._original_purchase_invoice.supplier} payable "
                                   f"increased by {instance._original_amount}")
                    
                    instance.purchase_invoice.paid_amount += instance.amount
                    instance.purchase_invoice.save(update_fields=['paid_amount'])
                    logger.info(f"New invoice #{instance.purchase_invoice.pk} paid amount "
                               f"increased by {instance.amount}")
                    
                    if instance.purchase_invoice.supplier:
                        instance.purchase_invoice.supplier.payable -= Decimal(str(instance.amount))
                        instance.purchase_invoice.supplier.save(update_fields=['payable'])
                        logger.info(f"New supplier {instance.purchase_invoice.supplier} payable "
                                   f"decreased by {instance.amount}")
                else:
                    # Same invoice but amount changed
                    delta = instance.amount - instance._original_amount
                    if delta != 0:
                        instance.purchase_invoice.paid_amount += delta
                        instance.purchase_invoice.save(update_fields=['paid_amount'])
                        logger.info(f"Invoice #{instance.purchase_invoice.pk} paid amount "
                                   f"adjusted by {delta}")
                        
                        if instance.purchase_invoice.supplier:
                            instance.purchase_invoice.supplier.payable -= Decimal(str(delta))
                            instance.purchase_invoice.supplier.save(update_fields=['payable'])
                            logger.info(f"Supplier {instance.purchase_invoice.supplier} payable "
                                       f"adjusted by -{delta}")


@receiver(pre_delete, sender=Payment)
def payment_pre_delete(sender, instance, **kwargs):
    """
    When a payment is deleted, reverse all the financial effects.
    
    This includes:
    1. Adding the amount back to the account balance
    2. Decreasing the invoice paid amount
    3. Increasing the supplier payable if applicable
    """
    with transaction.atomic():
        instance.account.balance += instance.amount
        instance.account.save(update_fields=['balance'])
        logger.info(f"Payment #{instance.pk} deleted, added {instance.amount} back to account {instance.account}")
        
        instance.purchase_invoice.paid_amount -= instance.amount
        instance.purchase_invoice.save(update_fields=['paid_amount'])
        logger.info(f"Reduced paid amount for purchase invoice #{instance.purchase_invoice.pk} by {instance.amount}")
        
        if instance.purchase_invoice.supplier:
            instance.purchase_invoice.supplier.payable += Decimal(str(instance.amount))
            instance.purchase_invoice.supplier.save(update_fields=['payable'])
            logger.info(f"Increased payable for supplier {instance.purchase_invoice.supplier} by {instance.amount}")