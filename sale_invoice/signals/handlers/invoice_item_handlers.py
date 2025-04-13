from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.dispatch import receiver
import logging

from sale_invoice.models import SalesInvoiceItem
from sale_invoice.signals.logic.invoice_item_logic import capture_original_sales_item_data, process_sales_item_creation, process_sales_item_deletion, process_sales_item_update, update_invoice_total_after_delete

# Set up logger
logger = logging.getLogger(__name__)

@receiver(pre_save, sender=SalesInvoiceItem)
def store_original_sales_item_data(sender, instance, **kwargs):
    """
    Store the original values before a SalesInvoiceItem is updated.
    
    This allows proper handling of stock quantities when item details change.
    """
    capture_original_sales_item_data(instance, logger)


@receiver(post_save, sender=SalesInvoiceItem)
def update_stock_on_sales_item_save(sender, instance, created, **kwargs):
    """
    Update stock quantities when a sales invoice item is created or updated.
    """
    if created:
        process_sales_item_creation(instance, logger)
    else:
        process_sales_item_update(instance, logger)


@receiver(pre_delete, sender=SalesInvoiceItem)
def update_stock_on_sales_item_delete(sender, instance, **kwargs):
    """
    When a sales invoice item is deleted, return the stock to inventory.
    """
    process_sales_item_deletion(instance, logger)


@receiver(post_delete, sender=SalesInvoiceItem)
def update_invoice_total_after_delete_handler(sender, instance, **kwargs):
    """
    Update the invoice total after an item is deleted.
    """
    update_invoice_total_after_delete(instance, logger)