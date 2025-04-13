from django.db.models.signals import pre_save, post_save, pre_delete
from django.dispatch import receiver
import logging

from receipt.models import Receipt
from receipt.signals.handlers.receipt_handlers import (
    capture_original_receipt_state,
    update_account_balance,
    update_invoice_customer,
    reverse_receipt_effects
)

# Set up logger
logger = logging.getLogger(__name__)

@receiver(pre_save, sender=Receipt)
def receipt_pre_save(sender, instance, **kwargs):
    """
    Capture the original state of a receipt before it's changed.
    
    This function saves the original amount, account, and sales_invoice 
    to enable proper handling of balance updates when these fields change.
    """
    capture_original_receipt_state(instance, logger)


@receiver(post_save, sender=Receipt)
def receipt_account_update(sender, instance, created, **kwargs):
    """
    Update account balance after receipt is saved.
    
    For new receipts, add the amount to the account balance.
    For updated receipts, handle account changes and amount changes appropriately.
    """
    update_account_balance(instance, created, logger)


@receiver(post_save, sender=Receipt)
def receipt_invoice_customer_update(sender, instance, created, **kwargs):
    """
    Update sales invoice paid amount and customer credit.
    
    For new receipts, increase invoice paid amount and decrease customer credit.
    For updated receipts, handle invoice changes and amount changes appropriately.
    """
    update_invoice_customer(instance, created, logger)


@receiver(pre_delete, sender=Receipt)
def receipt_pre_delete(sender, instance, **kwargs):
    """
    When a receipt is deleted, reverse all the financial effects.
    
    This includes:
    1. Removing the amount from the account balance
    2. Decreasing the invoice paid amount
    3. Increasing the customer credit if applicable
    """
    reverse_receipt_effects(instance, logger)