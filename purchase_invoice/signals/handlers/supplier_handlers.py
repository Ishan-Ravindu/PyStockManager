from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
import logging

from purchase_invoice.models import PurchaseInvoice
from purchase_invoice.signals.logic.supplier_logic import update_supplier_payable_on_create, update_supplier_payable_on_delete, update_supplier_payable_on_update

logger = logging.getLogger(__name__)

@receiver(post_save, sender=PurchaseInvoice)
def update_supplier_payable_on_invoice_save(sender, instance, created, **kwargs):
    """
    Update supplier payable balance when a purchase invoice is created or updated.
    """
    if created:
        update_supplier_payable_on_create(instance, logger)
    else:
        update_supplier_payable_on_update(instance, logger)


@receiver(post_delete, sender=PurchaseInvoice)
def update_supplier_payable_on_invoice_delete(sender, instance, **kwargs):
    """
    When a purchase invoice is deleted, reduce the supplier's payable balance accordingly.
    """
    update_supplier_payable_on_delete(instance, logger)