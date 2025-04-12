from django.db.models.signals import pre_save, post_save, pre_delete
from django.dispatch import receiver
from ..utils import safe_get_original
from ..logic.withdraw_logic import (
    handle_withdraw_create,
    handle_withdraw_update,
    handle_withdraw_delete,
)

@receiver(pre_save, sender='account.Withdraw')
def withdraw_pre_save(sender, instance, **kwargs):
    if instance.pk:
        safe_get_original(instance, 'Withdraw', ['amount', 'account'])

@receiver(post_save, sender='account.Withdraw')
def withdraw_post_save(sender, instance, created, **kwargs):
    if created:
        handle_withdraw_create(instance)
    elif hasattr(instance, '_original_amount') and hasattr(instance, '_original_account'):
        handle_withdraw_update(instance)

@receiver(pre_delete, sender='account.Withdraw')
def withdraw_pre_delete(sender, instance, **kwargs):
    handle_withdraw_delete(instance)
