from django.db import transaction

def handle_transfer_create(instance):
    with transaction.atomic():
        # Set history reason directly on transfer instance
        instance._change_reason  = getattr(instance, '_change_reason', 
            f"New transfer of {instance.amount} from {instance.from_account} to {instance.to_account} created")
        
        # Set history reason and update balance for from_account
        instance.from_account._change_reason  = getattr(instance.from_account, '_change_reason',
            f"Balance decreased by {instance.amount} due to transfer to {instance.to_account}")
        instance.from_account.balance -= instance.amount
        instance.from_account.save(update_fields=['balance'])
        
        # Set history reason and update balance for to_account
        instance.to_account._change_reason  = getattr(instance.to_account, '_change_reason',
            f"Balance increased by {instance.amount} due to transfer from {instance.from_account}")
        instance.to_account.balance += instance.amount
        instance.to_account.save(update_fields=['balance'])

def handle_transfer_update(instance):
    with transaction.atomic():
        # Determine the reason for the transfer update
        if hasattr(instance, '_change_reason'):
            reason = instance._change_reason
        elif (instance._original_from_account != instance.from_account or
              instance._original_to_account != instance.to_account):
            reason = (f"Transfer accounts changed from {instance._original_from_account} "
                      f"to {instance._original_to_account} to {instance.from_account} "
                      f"to {instance.to_account}")
        elif instance._original_amount != instance.amount:
            reason = f"Transfer amount changed from {instance._original_amount} to {instance.amount}"
        else:
            reason = "Transfer updated"
        
        # Set history reason for transfer instance
        instance._change_reason  = reason
        
        # Set history reason and update balance for original from_account
        instance._original_from_account._change_reason  = getattr(instance._original_from_account, '_change_reason',
            f"Balance increased by {instance._original_amount} due to transfer update/reversal")
        instance._original_from_account.balance += instance._original_amount
        instance._original_from_account.save(update_fields=['balance'])
        
        # Set history reason and update balance for original to_account
        instance._original_to_account._change_reason  = getattr(instance._original_to_account, '_change_reason',
            f"Balance decreased by {instance._original_amount} due to transfer update/reversal")
        instance._original_to_account.balance -= instance._original_amount
        instance._original_to_account.save(update_fields=['balance'])
        
        # Set history reason and update balance for new from_account
        instance.from_account._change_reason  = getattr(instance.from_account, '_change_reason',
            f"Balance decreased by {instance.amount} due to updated transfer to {instance.to_account}")
        instance.from_account.balance -= instance.amount
        instance.from_account.save(update_fields=['balance'])
        
        # Set history reason and update balance for new to_account
        instance.to_account._change_reason  = getattr(instance.to_account, '_change_reason',
            f"Balance increased by {instance.amount} due to updated transfer from {instance.from_account}")
        instance.to_account.balance += instance.amount
        instance.to_account.save(update_fields=['balance'])
        
        # Save the transfer instance after all related changes
        instance.save_without_historical_record = True
        instance.save(update_fields=['amount'])

def handle_transfer_delete(instance):
    with transaction.atomic():
        # Set history reason for transfer instance
        instance._change_reason  = getattr(instance, '_change_reason',
            f"Transfer of {instance.amount} from {instance.from_account} to {instance.to_account} deleted")
        
        # Set history reason and update balance for from_account
        instance.from_account._change_reason  = getattr(instance.from_account, '_change_reason',
            f"Balance increased by {instance.amount} due to deleted transfer to {instance.to_account}")
        instance.from_account.balance += instance.amount
        instance.from_account.save(update_fields=['balance'])
        
        # Set history reason and update balance for to_account
        instance.to_account._change_reason  = getattr(instance.to_account, '_change_reason',
            f"Balance decreased by {instance.amount} due to deleted transfer from {instance.from_account}")
        instance.to_account.balance -= instance.amount
        instance.to_account.save(update_fields=['balance'])