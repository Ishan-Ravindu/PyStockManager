from django.db.models.signals import pre_save, post_save, pre_delete
from django.dispatch import receiver
from django.db import transaction
from django.apps import apps

# Account Direct Balance Change Tracking
@receiver(pre_save, sender='accounts.Account')
def account_pre_save(sender, instance, **kwargs):
    """Track direct changes to the account balance field"""
    if instance.pk:
        try:
            Account = apps.get_model('accounts', 'Account')
            old_account = Account.objects.get(pk=instance.pk)
            if old_account.balance != instance.balance:
                instance._original_balance = old_account.balance
        except Account.DoesNotExist:
            pass

@receiver(post_save, sender='accounts.Account')
def account_post_save(sender, instance, created, **kwargs):
    """Record history for direct balance changes"""
    if not created and hasattr(instance, '_original_balance'):
        if instance._original_balance != instance.balance:
            AccountTransactionHistory = apps.get_model('accounts', 'AccountTransactionHistory')
            amount = instance.balance - instance._original_balance
            if not getattr(instance, '_skip_balance_history', False):
                history = AccountTransactionHistory(
                    account=instance,
                    amount=amount,
                    previous_balance=instance._original_balance,
                    new_balance=instance.balance,
                    transaction_type='ADJUSTMENT',
                    action_type='UPDATE',
                    description=f"Direct account balance change ({amount})"
                )
                history.save()

# Withdraw Signals
@receiver(pre_save, sender='accounts.Withdraw')
def withdraw_pre_save(sender, instance, **kwargs):
    """Handle balance updates when a withdrawal is being edited"""
    if instance.pk:
        try:
            Withdraw = apps.get_model('accounts', 'Withdraw')
            old_withdraw = Withdraw.objects.get(pk=instance.pk)
            instance._original_amount = old_withdraw.amount
            instance._original_account = old_withdraw.account
        except Withdraw.DoesNotExist:
            instance._original_amount = None
            instance._original_account = None

@receiver(post_save, sender='accounts.Withdraw')
def withdraw_post_save(sender, instance, created, **kwargs):
    """Handle balance updates after withdrawal is saved"""
    if created:
        with transaction.atomic():
            instance.account.update_balance(
                amount=-instance.amount,
                related_obj=instance,
                transaction_type='WITHDRAW',
                action_type='CREATE',
                description=f"Withdrawal of {instance.amount}"
            )
    else:
        if hasattr(instance, '_original_amount') and hasattr(instance, '_original_account'):
            with transaction.atomic():
                if instance._original_account != instance.account:
                    instance._original_account.update_balance(
                        amount=instance._original_amount,
                        related_obj=instance,
                        transaction_type='WITHDRAW',
                        action_type='UPDATE',
                        description=f"Refund of withdrawal {instance.pk} (account changed)"
                    )
                    instance.account.update_balance(
                        amount=-instance.amount,
                        related_obj=instance,
                        transaction_type='WITHDRAW',
                        action_type='UPDATE',
                        description=f"Withdrawal of {instance.amount} (updated from another account)"
                    )
                else:
                    delta = instance._original_amount - instance.amount
                    if delta != 0:
                        instance.account.update_balance(
                            amount=delta,
                            related_obj=instance,
                            transaction_type='WITHDRAW',
                            action_type='UPDATE',
                            description=f"Withdrawal amount changed from {instance._original_amount} to {instance.amount}"
                        )

@receiver(pre_delete, sender='accounts.Withdraw')
def withdraw_pre_delete(sender, instance, **kwargs):
    """When a withdrawal is deleted, refund the amount back to the account"""
    with transaction.atomic():
        instance.account.update_balance(
            amount=instance.amount,
            related_obj=instance,
            transaction_type='WITHDRAW',
            action_type='DELETE',
            description=f"Refund of deleted withdrawal {instance.pk}"
        )

# Account Transfer Signals
@receiver(pre_save, sender='accounts.AccountTransfer')
def transfer_pre_save(sender, instance, **kwargs):
    """Handle balance updates when a transfer is being edited"""
    if instance.pk:
        try:
            AccountTransfer = apps.get_model('accounts', 'AccountTransfer')
            old_transfer = AccountTransfer.objects.get(pk=instance.pk)
            instance._original_amount = old_transfer.amount
            instance._original_from_account = old_transfer.from_account
            instance._original_to_account = old_transfer.to_account
        except AccountTransfer.DoesNotExist:
            instance._original_amount = None
            instance._original_from_account = None
            instance._original_to_account = None

@receiver(post_save, sender='accounts.AccountTransfer')
def transfer_post_save(sender, instance, created, **kwargs):
    """Handle balance updates after transfer is saved"""
    if created:
        with transaction.atomic():
            instance.from_account.update_balance(
                amount=-instance.amount,
                related_obj=instance,
                transaction_type='TRANSFER_OUT',
                action_type='CREATE',
                description=f"Transfer of {instance.amount} to {instance.to_account}"
            )
            instance.to_account.update_balance(
                amount=instance.amount,
                related_obj=instance,
                transaction_type='TRANSFER_IN',
                action_type='CREATE',
                description=f"Transfer of {instance.amount} from {instance.from_account}"
            )
    else:
        if (hasattr(instance, '_original_amount') and
                hasattr(instance, '_original_from_account') and
                hasattr(instance, '_original_to_account')):            
            with transaction.atomic():
                if instance._original_from_account:
                    instance._original_from_account.update_balance(
                        amount=instance._original_amount,
                        related_obj=instance,
                        transaction_type='TRANSFER_OUT',
                        action_type='UPDATE',
                        description=f"Reversal of transfer {instance.pk} ({instance._original_amount})"
                    )
                
                if instance._original_to_account:
                    instance._original_to_account.update_balance(
                        amount=-instance._original_amount,
                        related_obj=instance,
                        transaction_type='TRANSFER_IN',
                        action_type='UPDATE',
                        description=f"Reversal of transfer {instance.pk} ({instance._original_amount})"
                    )
                instance.from_account.update_balance(
                    amount=-instance.amount,
                    related_obj=instance,
                    transaction_type='TRANSFER_OUT',
                    action_type='UPDATE',
                    description=f"Updated transfer of {instance.amount} to {instance.to_account}"
                )                
                instance.to_account.update_balance(
                    amount=instance.amount,
                    related_obj=instance,
                    transaction_type='TRANSFER_IN',
                    action_type='UPDATE',
                    description=f"Updated transfer of {instance.amount} from {instance.from_account}"
                )

@receiver(pre_delete, sender='accounts.AccountTransfer')
def transfer_pre_delete(sender, instance, **kwargs):
    """When a transfer is deleted, reverse the amounts for both accounts"""
    with transaction.atomic():
        instance.from_account.update_balance(
            amount=instance.amount,
            related_obj=instance,
            transaction_type='TRANSFER_OUT',
            action_type='DELETE',
            description=f"Reversal of deleted transfer {instance.pk}"
        )
        
        instance.to_account.update_balance(
            amount=-instance.amount,
            related_obj=instance,
            transaction_type='TRANSFER_IN',
            action_type='DELETE',
            description=f"Reversal of deleted transfer {instance.pk}"
        )