from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
import logging

from purchase_invoice.models import PurchaseInvoice, PurchaseInvoiceItem
from purchase_invoice.signals.logic.supplier_logic import (
    handle_invoice_save,
    handle_invoice_item_save,
    handle_invoice_item_delete
)

logger = logging.getLogger(__name__)

@receiver(pre_save, sender=PurchaseInvoice)
def capture_original_invoice_data(sender, instance, **kwargs):
    """
    Capture original data from the invoice before it is saved.
    This data is needed by the supplier payable update logic.
    """
    if instance.pk:  # Only for existing objects being updated
        try:
            # Get original instance from database
            original = PurchaseInvoice.objects.get(pk=instance.pk)
            
            # Store values needed for supplier payable calculations
            instance._original_supplier = original.supplier
            instance._original_total_amount = original.total_amount
            
            logger.debug(f"Captured original invoice data: supplier={original.supplier}, "
                        f"total_amount={original.total_amount}")
        except PurchaseInvoice.DoesNotExist:
            logger.warning(f"Could not find original invoice with ID {instance.pk}")


@receiver(post_save, sender=PurchaseInvoice)
def update_supplier_payable_on_invoice_save(sender, instance, created, **kwargs):
    """
    Update supplier payable balance when a purchase invoice is created or updated.
    This signal handler delegates to the business logic layer.
    """
    handle_invoice_save(instance, created, logger)


@receiver(post_delete, sender=PurchaseInvoice)
def update_supplier_payable_on_invoice_delete(sender, instance, **kwargs):
    """
    When a purchase invoice is deleted, reduce the supplier's payable balance accordingly.
    """
    from purchase_invoice.signals.logic.supplier_logic import update_supplier_payable_on_delete
    update_supplier_payable_on_delete(instance, logger)


@receiver(pre_save, sender=PurchaseInvoiceItem)
def capture_original_invoice_item_data(sender, instance, **kwargs):
    """
    Capture original data from invoice item before it is saved.
    """
    if instance.pk:  # Only for existing objects being updated
        try:
            original = PurchaseInvoiceItem.objects.get(pk=instance.pk)
            
            # Store original values
            instance._original_invoice = original.purchase_invoice
            instance._original_invoice_total = original.purchase_invoice.total_amount
            instance._original_quantity = original.quantity
            instance._original_price = original.price
            instance._original_item_total = original.price * original.quantity
            
            logger.debug(f"Captured original invoice item data: quantity={original.quantity}, "
                        f"price={original.price}, invoice_total={original.purchase_invoice.total_amount}")
        except PurchaseInvoiceItem.DoesNotExist:
            logger.warning(f"Could not find original invoice item with ID {instance.pk}")


@receiver(post_save, sender=PurchaseInvoiceItem)
def update_invoice_and_supplier_after_item_save(sender, instance, created, **kwargs):
    """
    Update the invoice's total amount and supplier payable when an item is saved.
    This signal handler delegates to the business logic layer.
    """
    handle_invoice_item_save(instance, created, logger)


@receiver(post_delete, sender=PurchaseInvoiceItem)
def update_supplier_after_item_delete(sender, instance, **kwargs):
    """
    Update supplier payable when an invoice item is deleted.
    This signal handler delegates to the business logic layer.
    """
    handle_invoice_item_delete(instance, logger)