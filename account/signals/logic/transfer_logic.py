from django.db import transaction
from ..utils import save_balance, set_change_reason

def handle_transfer_create(instance):
    with transaction.atomic():
        save_balance(instance.from_account, -instance.amount)
        save_balance(instance.to_account, instance.amount)
        set_change_reason(
            instance,
            f"New transfer of {instance.amount} from {instance.from_account} to {instance.to_account} created"
        )

def handle_transfer_update(instance):
    with transaction.atomic():
        save_balance(instance._original_from_account, instance._original_amount)
        save_balance(instance._original_to_account, -instance._original_amount)
        save_balance(instance.from_account, -instance.amount)
        save_balance(instance.to_account, instance.amount)

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

        set_change_reason(instance, reason)
        instance.save_without_historical_record = True
        instance.save(update_fields=['amount'])

def handle_transfer_delete(instance):
    with transaction.atomic():
        save_balance(instance.from_account, instance.amount)
        save_balance(instance.to_account, -instance.amount)
        set_change_reason(
            instance,
            f"Transfer of {instance.amount} from {instance.from_account} to {instance.to_account} deleted"
        )
