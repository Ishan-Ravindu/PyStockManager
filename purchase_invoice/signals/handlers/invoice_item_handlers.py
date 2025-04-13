from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
import logging

from inventory.signals.logic.stock_transfer_logic import capture_original_item_data
from purchase_invoice.models import PurchaseInvoice, PurchaseInvoiceItem
from purchase_invoice.signals.logic.invoice_item_logic import process_purchase_item_creation, process_purchase_item_deletion, process_purchase_item_update

logger = logging.getLogger(__name__)

@receiver(pre_save, sender=PurchaseInvoiceItem)
def store_original_item_data(sender, instance, **kwargs):
    """
    Store the original values before a PurchaseInvoiceItem is updated.
    
    This allows proper handling of stock quantities and average costs when
    item details change.
    """
    capture_original_item_data(instance, logger)


@receiver(post_save, sender=PurchaseInvoiceItem)
def update_stock_on_purchase_item_save(sender, instance, created, **kwargs):
    """
    Update stock when a purchase invoice item is created or updated.
    """
    if created:
        process_purchase_item_creation(instance, logger)
    else:
        process_purchase_item_update(instance, logger)


@receiver(post_delete, sender=PurchaseInvoiceItem)
def update_stock_on_purchase_item_delete(sender, instance, **kwargs):
    """
    When a purchase invoice item is deleted, reverse the stock changes.
    """
    process_purchase_item_deletion(instance, logger)