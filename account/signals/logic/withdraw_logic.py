from django.db import transaction

def handle_withdraw_create(instance):
    with transaction.atomic():
        # Set history reason directly on instances
        instance._change_reason  = getattr(instance, '_change_reason', f"New withdrawal of {instance.amount} created")
        instance.account._change_reason  = getattr(instance.account, '_change_reason', f"Balance decreased by {instance.amount} due to withdrawal")
        
        # Update account balance
        instance.account.balance -= instance.amount
        instance.account.save(update_fields=['balance'])

def handle_withdraw_update(instance):
    with transaction.atomic():
        if instance._original_account != instance.account:
            # Set history reasons directly on instances
            instance._change_reason  = getattr(instance, '_change_reason', 
                f"Withdrawal transferred from {instance._original_account} to {instance.account}")
            
            instance._original_account._change_reason  = getattr(instance._original_account, '_change_reason',
                f"Balance increased by {instance._original_amount} due to withdrawal transfer to {instance.account}")
            
            # Update original account balance
            instance._original_account.balance += instance._original_amount
            instance._original_account.save(update_fields=['balance'])
            
            # Set history reason for new account
            instance.account._change_reason  = getattr(instance.account, '_change_reason',
                f"Balance decreased by {instance.amount} due to withdrawal transferred from {instance._original_account}")
            
            # Update new account balance
            instance.account.balance -= instance.amount
            instance.account.save(update_fields=['balance'])
        else:
            delta = instance._original_amount - instance.amount
            if delta != 0:
                # Set history reason for withdrawal instance
                instance._change_reason  = getattr(instance, '_change_reason',
                    f"Withdrawal amount changed from {instance._original_amount} to {instance.amount}")
                
                # Determine appropriate description for account change
                if delta > 0:
                    change_description = f"Balance increased by {delta} due to withdrawal amount reduction"
                else:
                    change_description = f"Balance decreased by {abs(delta)} due to withdrawal amount increase"
                
                # Set history reason for account
                instance.account._change_reason  = getattr(instance.account, '_change_reason', change_description)
                
                # Update account balance
                instance.account.balance += delta
                instance.account.save(update_fields=['balance'])

        # Save the withdrawal instance after all related changes
        instance.save_without_historical_record = True
        instance.save(update_fields=['amount'])

def handle_withdraw_delete(instance):
    with transaction.atomic():
        # Set history reasons directly on instances
        instance._change_reason  = getattr(instance, '_change_reason', 
            f"Withdrawal of {instance.amount} deleted")
        
        instance.account._change_reason  = getattr(instance.account, '_change_reason',
            f"Balance increased by {instance.amount} due to withdrawal deletion")
        
        # Update account balance
        instance.account.balance += instance.amount
        instance.account.save(update_fields=['balance'])