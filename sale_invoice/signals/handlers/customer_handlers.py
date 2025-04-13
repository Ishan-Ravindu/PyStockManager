from django.db.models.signals import pre_save, post_save, pre_delete
from django.dispatch import receiver
import logging

from sale_invoice.models import SalesInvoice, SalesInvoiceItem
from sale_invoice.signals.logic.customer_logic import capture_original_invoice_data, handle_invoice_deletion, process_invoice_customer_change

# Set up logger
logger = logging.getLogger(__name__)

@receiver(pre_save, sender=SalesInvoice)
def store_original_invoice_data(sender, instance, **kwargs):
    """
    Store the original shop and customer data before a SalesInvoice is updated.
    
    This allows proper handling of shop stock and customer credit changes.
    """
    capture_original_invoice_data(instance, logger)


@receiver(post_save, sender=SalesInvoice)
def handle_invoice_customer_change(sender, instance, created, **kwargs):
    """
    When a sales invoice's customer is changed, update customer credits.
    """
    process_invoice_customer_change(instance, created, logger)


@receiver(pre_delete, sender=SalesInvoice)
def handle_invoice_delete(sender, instance, **kwargs):
    """
    When a sales invoice is deleted, update customer credit.
    """
    handle_invoice_deletion(instance, logger)