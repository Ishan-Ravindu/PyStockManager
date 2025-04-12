from django.db.models.signals import pre_save, post_save, pre_delete
from django.dispatch import receiver
from ..utils import safe_get_original
from ..logic.transfer_logic import (
    handle_transfer_create,
    handle_transfer_update,
    handle_transfer_delete,
)

@receiver(pre_save, sender='account.AccountTransfer')
def transfer_pre_save(sender, instance, **kwargs):
    if instance.pk:
        safe_get_original(instance, 'AccountTransfer', ['amount', 'from_account', 'to_account'])

@receiver(post_save, sender='account.AccountTransfer')
def transfer_post_save(sender, instance, created, **kwargs):
    if created:
        handle_transfer_create(instance)
    elif all(hasattr(instance, f'_original_{f}') for f in ['amount', 'from_account', 'to_account']):
        handle_transfer_update(instance)

@receiver(pre_delete, sender='account.AccountTransfer')
def transfer_pre_delete(sender, instance, **kwargs):
    handle_transfer_delete(instance)
