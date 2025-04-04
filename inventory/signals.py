from django.db.models.signals import pre_save, post_save, pre_delete
from django.dispatch import receiver
from django.db import transaction
from django.apps import apps

from .models import Receipt

# Receipt Signals
@receiver(pre_save, sender=Receipt)
def receipt_pre_save(sender, instance, **kwargs):
    """Capture the original state of a receipt before it's changed"""
    if instance.pk:
        try:
            old_receipt = Receipt.objects.get(pk=instance.pk)
            instance._original_amount = old_receipt.amount
            instance._original_account = old_receipt.account
            instance._original_sales_invoice = old_receipt.sales_invoice
        except Receipt.DoesNotExist:
            instance._original_amount = None
            instance._original_account = None
            instance._original_sales_invoice = None


@receiver(post_save, sender=Receipt)
def receipt_account_update(sender, instance, created, **kwargs):
    """Update account balance after receipt is saved"""
    if created:
        with transaction.atomic():
            instance.account.update_balance(
                amount=instance.amount,
                related_obj=instance,
                transaction_type='DEPOSIT',
                action_type='CREATE',
                description=f"Receipt #{instance.pk} for Sales Invoice #{instance.sales_invoice.pk}"
            )
    else:
        if hasattr(instance, '_original_amount') and hasattr(instance, '_original_account'):
            with transaction.atomic():
                if instance._original_account != instance.account:
                    instance._original_account.update_balance(
                        amount=-instance._original_amount,
                        related_obj=instance,
                        transaction_type='DEPOSIT',
                        action_type='UPDATE',
                        description=f"Reversal of Receipt #{instance.pk} (account changed)"
                    )
                    instance.account.update_balance(
                        amount=instance.amount,
                        related_obj=instance,
                        transaction_type='DEPOSIT',
                        action_type='UPDATE',
                        description=f"Receipt #{instance.pk} (updated to this account)"
                    )
                else:
                    delta = instance.amount - instance._original_amount
                    if delta != 0:
                        instance.account.update_balance(
                            amount=delta,
                            related_obj=instance,
                            transaction_type='DEPOSIT',
                            action_type='UPDATE',
                            description=f"Receipt #{instance.pk} amount changed from {instance._original_amount} to {instance.amount}"
                        )


@receiver(post_save, sender=Receipt)
def receipt_invoice_customer_update(sender, instance, created, **kwargs):
    """Update sales invoice paid amount and customer credit"""
    if created:
        with transaction.atomic():
            instance.sales_invoice.paid_amount += instance.amount
            instance.sales_invoice.save(update_fields=['paid_amount'])
            if instance.sales_invoice.customer:
                instance.sales_invoice.customer.credit -= instance.amount
                instance.sales_invoice.customer.save(update_fields=['credit'])
    else:
        if hasattr(instance, '_original_amount') and hasattr(instance, '_original_sales_invoice'):
            with transaction.atomic():
                if instance._original_sales_invoice != instance.sales_invoice:
                    instance._original_sales_invoice.paid_amount -= instance._original_amount
                    instance._original_sales_invoice.save(update_fields=['paid_amount'])
                    if instance._original_sales_invoice.customer:
                        instance._original_sales_invoice.customer.credit += instance._original_amount
                        instance._original_sales_invoice.customer.save(update_fields=['credit'])
                    instance.sales_invoice.paid_amount += instance.amount
                    instance.sales_invoice.save(update_fields=['paid_amount'])
                    if instance.sales_invoice.customer:
                        instance.sales_invoice.customer.credit -= instance.amount
                        instance.sales_invoice.customer.save(update_fields=['credit'])                
                else:
                    delta = instance.amount - instance._original_amount
                    if delta != 0:
                        instance.sales_invoice.paid_amount += delta
                        instance.sales_invoice.save(update_fields=['paid_amount'])
                        if instance.sales_invoice.customer:
                            instance.sales_invoice.customer.credit -= delta
                            instance.sales_invoice.customer.save(update_fields=['credit'])


@receiver(pre_delete, sender=Receipt)
def receipt_pre_delete(sender, instance, **kwargs):
    """When a receipt is deleted, remove the money from the account"""
    with transaction.atomic():
        instance.account.update_balance(
            amount=-instance.amount,
            related_obj=instance,
            transaction_type='DEPOSIT',
            action_type='DELETE',
            description=f"Deletion of Receipt #{instance.pk} for Sales Invoice #{instance.sales_invoice.pk}"
        )
        instance.sales_invoice.paid_amount -= instance.amount
        instance.sales_invoice.save(update_fields=['paid_amount'])
        if instance.sales_invoice.customer:
            instance.sales_invoice.customer.credit += instance.amount
            instance.sales_invoice.customer.save(update_fields=['credit'])