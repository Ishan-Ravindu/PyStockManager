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
            instance._original_purchase_invoice = old_payment.purchase_invoice
        except Payment.DoesNotExist:
            instance._original_amount = None
            instance._original_account = None
            instance._original_purchase_invoice = None


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
        instance._history_change_reason = getattr(instance, '_change_reason', reason)
        logger.info(f"[Account] Payment #{instance.pk} processed. Reason: {instance._history_change_reason}")


def update_invoice_and_supplier_on_payment_save(instance, created):
    with transaction.atomic():
        if created:
            instance.purchase_invoice.paid_amount += instance.amount
            reason = f"Payment created: Invoice #{instance.purchase_invoice.pk} paid {instance.amount}"
            instance.purchase_invoice.save(update_fields=['paid_amount'])
            if instance.purchase_invoice.supplier:
                instance.purchase_invoice.supplier.payable -= Decimal(str(instance.amount))
                instance.purchase_invoice.supplier.save(update_fields=['payable'])
        else:
            if hasattr(instance, '_original_amount') and hasattr(instance, '_original_purchase_invoice'):
                if instance._original_purchase_invoice != instance.purchase_invoice:
                    instance._original_purchase_invoice.paid_amount -= instance._original_amount
                    instance._original_purchase_invoice.save(update_fields=['paid_amount'])
                    if instance._original_purchase_invoice.supplier:
                        instance._original_purchase_invoice.supplier.payable += Decimal(str(instance._original_amount))
                        instance._original_purchase_invoice.supplier.save(update_fields=['payable'])

                    instance.purchase_invoice.paid_amount += instance.amount
                    instance.purchase_invoice.save(update_fields=['paid_amount'])
                    if instance.purchase_invoice.supplier:
                        instance.purchase_invoice.supplier.payable -= Decimal(str(instance.amount))
                        instance.purchase_invoice.supplier.save(update_fields=['payable'])
                    reason = f"Invoice changed on Payment #{instance.pk}"
                else:
                    delta = instance.amount - instance._original_amount
                    instance.purchase_invoice.paid_amount += delta
                    instance.purchase_invoice.save(update_fields=['paid_amount'])
                    if instance.purchase_invoice.supplier:
                        instance.purchase_invoice.supplier.payable -= Decimal(str(delta))
                        instance.purchase_invoice.supplier.save(update_fields=['payable'])
                    reason = f"Invoice #{instance.purchase_invoice.pk} adjusted by {delta}"
        instance._history_change_reason = getattr(instance, '_change_reason', reason)
        logger.info(f"[Invoice] Payment #{instance.pk} processed. Reason: {instance._history_change_reason}")


def handle_payment_delete(instance):
    with transaction.atomic():
        instance.account.balance += instance.amount
        instance.account.save(update_fields=['balance'])

        instance.purchase_invoice.paid_amount -= instance.amount
        instance.purchase_invoice.save(update_fields=['paid_amount'])

        if instance.purchase_invoice.supplier:
            instance.purchase_invoice.supplier.payable += Decimal(str(instance.amount))
            instance.purchase_invoice.supplier.save(update_fields=['payable'])

        instance._history_change_reason = f"Payment #{instance.pk} deleted, reverted changes"
        logger.info(f"[Delete] Payment #{instance.pk} deleted. Reason: {instance._history_change_reason}")

