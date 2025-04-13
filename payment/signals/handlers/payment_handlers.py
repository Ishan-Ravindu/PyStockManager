from django.db.models.signals import pre_save, post_save, pre_delete
from django.dispatch import receiver
from payment.models import Payment
from ..logic.payment_logic import (
    capture_original_payment_state,
    update_account_on_payment_save,
    update_invoice_and_supplier_on_payment_save,
    handle_payment_delete
)

@receiver(pre_save, sender=Payment)
def payment_pre_save(sender, instance, **kwargs):
    capture_original_payment_state(instance)

@receiver(post_save, sender=Payment)
def payment_post_save_account(sender, instance, created, **kwargs):
    update_account_on_payment_save(instance, created)

@receiver(post_save, sender=Payment)
def payment_post_save_invoice(sender, instance, created, **kwargs):
    update_invoice_and_supplier_on_payment_save(instance, created)

@receiver(pre_delete, sender=Payment)
def payment_pre_delete(sender, instance, **kwargs):
    handle_payment_delete(instance)