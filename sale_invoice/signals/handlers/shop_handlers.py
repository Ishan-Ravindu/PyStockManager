from django.db.models.signals import post_save
from django.dispatch import receiver
import logging

from sale_invoice.models import SalesInvoice
from sale_invoice.signals.logic.shop_logic import process_invoice_shop_change

# Set up logger
logger = logging.getLogger(__name__)

@receiver(post_save, sender=SalesInvoice)
def handle_invoice_shop_change(sender, instance, created, **kwargs):
    """
    When a sales invoice's shop is changed, update all associated items' stock.
    """
    if created:
        return  # New invoices are handled by the SalesInvoiceItem signals
    
    process_invoice_shop_change(instance, logger)