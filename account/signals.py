from django.db.models.signals import pre_save, post_save, pre_delete
from django.dispatch import receiver
from django.db import transaction
from django.apps import apps

# Withdraw Signals
@receiver(pre_save, sender='account.Withdraw')
def withdraw_pre_save(sender, instance, **kwargs):
    """Handle balance updates when a withdrawal is being edited"""
    if instance.pk:
        try:
            Withdraw = apps.get_model('account', 'Withdraw')
            old_withdraw = Withdraw.objects.get(pk=instance.pk)
            instance._original_amount = old_withdraw.amount
            instance._original_account = old_withdraw.account
        except Withdraw.DoesNotExist:
            instance._original_amount = None
            instance._original_account = None

@receiver(post_save, sender='account.Withdraw')
def withdraw_post_save(sender, instance, created, **kwargs):
    """Handle balance updates after withdrawal is saved"""
    if created:
        with transaction.atomic():
            instance.account.balance -= instance.amount
            instance.account.save(update_fields=['balance'])
    else:
        if hasattr(instance, '_original_amount') and hasattr(instance, '_original_account'):
            with transaction.atomic():
                if instance._original_account != instance.account:
                    instance._original_account.balance += instance._original_amount
                    instance._original_account.save(update_fields=['balance'])
                    
                    instance.account.balance -= instance.amount
                    instance.account.save(update_fields=['balance'])
                else:
                    delta = instance._original_amount - instance.amount
                    if delta != 0:
                        instance.account.balance += delta
                        instance.account.save(update_fields=['balance'])

@receiver(pre_delete, sender='account.Withdraw')
def withdraw_pre_delete(sender, instance, **kwargs):
    """When a withdrawal is deleted, refund the amount back to the account"""
    with transaction.atomic():
        instance.account.balance += instance.amount
        instance.account.save(update_fields=['balance'])

# Account Transfer Signals
@receiver(pre_save, sender='account.AccountTransfer')
def transfer_pre_save(sender, instance, **kwargs):
    """Handle balance updates when a transfer is being edited"""
    if instance.pk:
        try:
            AccountTransfer = apps.get_model('account', 'AccountTransfer')
            old_transfer = AccountTransfer.objects.get(pk=instance.pk)
            instance._original_amount = old_transfer.amount
            instance._original_from_account = old_transfer.from_account
            instance._original_to_account = old_transfer.to_account
        except AccountTransfer.DoesNotExist:
            instance._original_amount = None
            instance._original_from_account = None
            instance._original_to_account = None

@receiver(post_save, sender='account.AccountTransfer')
def transfer_post_save(sender, instance, created, **kwargs):
    """Handle balance updates after transfer is saved"""
    if created:
        with transaction.atomic():
            instance.from_account.balance -= instance.amount
            instance.from_account.save(update_fields=['balance'])
            
            instance.to_account.balance += instance.amount
            instance.to_account.save(update_fields=['balance'])
    else:
        if (hasattr(instance, '_original_amount') and
                hasattr(instance, '_original_from_account') and
                hasattr(instance, '_original_to_account')):            
            with transaction.atomic():
                if instance._original_from_account:
                    instance._original_from_account.balance += instance._original_amount
                    instance._original_from_account.save(update_fields=['balance'])
                
                if instance._original_to_account:
                    instance._original_to_account.balance -= instance._original_amount
                    instance._original_to_account.save(update_fields=['balance'])
                
                instance.from_account.balance -= instance.amount
                instance.from_account.save(update_fields=['balance'])
                
                instance.to_account.balance += instance.amount
                instance.to_account.save(update_fields=['balance'])

@receiver(pre_delete, sender='account.AccountTransfer')
def transfer_pre_delete(sender, instance, **kwargs):
    """When a transfer is deleted, reverse the amounts for both accounts"""
    with transaction.atomic():
        instance.from_account.balance += instance.amount
        instance.from_account.save(update_fields=['balance'])
        
        instance.to_account.balance -= instance.amount
        instance.to_account.save(update_fields=['balance'])