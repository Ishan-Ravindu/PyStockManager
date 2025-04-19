from django.db import transaction
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


def capture_original_payment_state(instance):
    if instance.pk:
        from payment.models import Payment
        try:
            old_payment = Payment.objects.get(pk=instance.pk)
            instance._original_amount = old_payment.amount
            instance._original_account = old_payment.account
            instance._original_payable = old_payment.payable
        except Payment.DoesNotExist:
            instance._original_amount = None
            instance._original_account = None
            instance._original_payable = None


def update_account_on_payment_save(instance, created):
    with transaction.atomic():
        if created:
            instance.account.balance -= instance.amount
            reason = f"Payment created for {instance.amount} from account {instance.account}"
        else:
            if hasattr(instance, '_original_amount') and hasattr(instance, '_original_account'):
                if instance._original_account != instance.account:
                    instance._original_account.balance += instance._original_amount
                    instance.account.balance -= instance.amount
                    instance._original_account.save(update_fields=['balance'])
                    reason = (
                        f"Payment account changed from {instance._original_account} to {instance.account} "
                        f"for amount {instance.amount}"
                    )
                else:
                    delta = instance.amount - instance._original_amount
                    instance.account.balance -= delta
                    reason = f"Payment amount updated from {instance._original_amount} to {instance.amount}"

        instance.account.save(update_fields=['balance'])
        instance._change_reason = getattr(instance, '_change_reason', reason)
        logger.info(f"[Account] Payment #{instance.pk} processed. Reason: {instance._change_reason}")


def update_payable_object_on_payment_save(instance, created):
    from purchase_invoice.models import PurchaseInvoice
    from expense.models import Expense
    
    payable = instance.payable
    reason = ""

    with transaction.atomic():
        if created:
            if isinstance(payable, PurchaseInvoice):
                payable.paid_amount += instance.amount
                payable.save(update_fields=['paid_amount'])
                reason = f"Invoice #{payable.pk} paid {instance.amount}"

                if payable.supplier:
                    payable.supplier.payable -= instance.amount
                    payable.supplier.save(update_fields=['payable'])

            elif isinstance(payable, Expense):
                payable.paid_amount += instance.amount
                payable.save(update_fields=['paid_amount'])
                reason = f"Expense #{payable.pk} paid {instance.amount}"

        else:
            if hasattr(instance, '_original_amount') and hasattr(instance, '_original_payable'):
                if instance._original_payable != payable:
                    # Rollback from old
                    if isinstance(instance._original_payable, PurchaseInvoice):
                        instance._original_payable.paid_amount -= instance._original_amount
                        instance._original_payable.save(update_fields=['paid_amount'])
                        if instance._original_payable.supplier:
                            instance._original_payable.supplier.payable += instance._original_amount
                            instance._original_payable.supplier.save(update_fields=['payable'])

                    elif isinstance(instance._original_payable, Expense):
                        instance._original_payable.paid_amount -= instance._original_amount
                        instance._original_payable.save(update_fields=['paid_amount'])

                    # Apply to new
                    if isinstance(payable, PurchaseInvoice):
                        payable.paid_amount += instance.amount
                        payable.save(update_fields=['paid_amount'])
                        if payable.supplier:
                            payable.supplier.payable -= instance.amount
                            payable.supplier.save(update_fields=['payable'])

                    elif isinstance(payable, Expense):
                        payable.paid_amount += instance.amount
                        payable.save(update_fields=['paid_amount'])

                    reason = f"Payable object changed on Payment #{instance.pk}"

                else:
                    delta = instance.amount - instance._original_amount
                    if isinstance(payable, PurchaseInvoice):
                        payable.paid_amount += delta
                        payable.save(update_fields=['paid_amount'])
                        if payable.supplier:
                            payable.supplier.payable -= delta
                            payable.supplier.save(update_fields=['payable'])

                    elif isinstance(payable, Expense):
                        payable.paid_amount += delta
                        payable.save(update_fields=['paid_amount'])

                    reason = f"Payable #{payable.pk} adjusted by {delta}"

        instance._change_reason = getattr(instance, '_change_reason', reason)
        logger.info(f"[Payable] Payment #{instance.pk} processed. Reason: {instance._change_reason}")


def handle_payment_delete(instance):
    from purchase_invoice.models import PurchaseInvoice
    from expense.models import Expense

    payable = instance.payable

    with transaction.atomic():
        instance.account.balance += instance.amount
        instance.account.save(update_fields=['balance'])

        if isinstance(payable, PurchaseInvoice):
            payable.paid_amount -= instance.amount
            payable.save(update_fields=['paid_amount'])

            if payable.supplier:
                payable.supplier.payable += instance.amount
                payable.supplier.save(update_fields=['payable'])

        elif isinstance(payable, Expense):
            payable.paid_amount -= instance.amount
            payable.save(update_fields=['paid_amount'])

        instance._change_reason = f"Payment #{instance.pk} deleted, reverted changes"
        logger.info(f"[Delete] Payment #{instance.pk} deleted. Reason: {instance._change_reason}")
