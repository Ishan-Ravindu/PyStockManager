from django.db import transaction
from ..utils import save_balance, set_change_reason

def handle_withdraw_create(instance):
    with transaction.atomic():
        save_balance(instance.account, -instance.amount)
        set_change_reason(instance, f"New withdrawal of {instance.amount} created")

def handle_withdraw_update(instance):
    with transaction.atomic():
        if instance._original_account != instance.account:
            save_balance(instance._original_account, instance._original_amount)
            save_balance(instance.account, -instance.amount)
            set_change_reason(
                instance,
                f"Withdrawal transferred from {instance._original_account} to {instance.account}"
            )
        else:
            delta = instance._original_amount - instance.amount
            if delta != 0:
                save_balance(instance.account, delta)
                set_change_reason(
                    instance,
                    f"Withdrawal amount changed from {instance._original_amount} to {instance.amount}"
                )
        instance.save_without_historical_record = True
        instance.save(update_fields=['amount'])

def handle_withdraw_delete(instance):
    with transaction.atomic():
        save_balance(instance.account, instance.amount)
        set_change_reason(instance, f"Withdrawal of {instance.amount} deleted")
