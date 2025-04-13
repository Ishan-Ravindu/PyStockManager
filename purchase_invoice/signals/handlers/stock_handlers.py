from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
import logging

from purchase_invoice.models import PurchaseInvoice
from purchase_invoice.signals.logic.stock_logic import capture_original_invoice_data, process_invoice_shop_changes

logger = logging.getLogger(__name__)

@receiver(pre_save, sender=PurchaseInvoice)
def store_original_invoice_data(sender, instance, **kwargs):
    """
    Store the original shop and supplier values before a PurchaseInvoice is updated.
    
    This is necessary to correctly handle stock and payable adjustments when the invoice's
    shop or supplier is changed.
    """
    capture_original_invoice_data(instance, logger)


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
    
    process_invoice_shop_changes(instance, logger)