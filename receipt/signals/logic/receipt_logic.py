from django.db import transaction

from receipt.models import Receipt


def capture_original_receipt_state(instance):
    """
    Capture the original state of a receipt before it's changed.
    
    Args:
        instance: The Receipt instance being saved
    """
    if instance.pk:
        try:
            old_receipt = Receipt.objects.get(pk=instance.pk)
            instance._original_amount = old_receipt.amount
            instance._original_account = old_receipt.account
            instance._original_sales_invoice = old_receipt.sales_invoice
        except Receipt.DoesNotExist:
            # New instance or instance was deleted
            instance._original_amount = None
            instance._original_account = None
            instance._original_sales_invoice = None

def update_account_balance(instance, created):
    """
    Update account balance after receipt is saved.
    
    Args:
        instance: The Receipt instance that was saved
        created: Boolean indicating if this is a new instance
    """
    if created:
        with transaction.atomic():
            # Set history reason for new receipt
            instance._change_reason = getattr(instance, '_change_reason', 
                f"New receipt of {instance.amount} created for invoice {instance.sales_invoice}")
            
            # Set history reason for account
            instance.account._change_reason = getattr(instance.account, '_change_reason',
                f"Balance increased by {instance.amount} due to new receipt for invoice {instance.sales_invoice}")
            
            # Update account balance
            instance.account.balance += instance.amount
            instance.account.save(update_fields=['balance'])           
    else:
        if hasattr(instance, '_original_amount') and hasattr(instance, '_original_account'):
            with transaction.atomic():
                if instance._original_account != instance.account:
                    # Account changed, set appropriate history reasons
                    instance._change_reason = getattr(instance, '_change_reason',
                        f"Receipt account changed from {instance._original_account} to {instance.account}")
                    
                    # Set history reason and update original account
                    instance._original_account._change_reason = getattr(instance._original_account, '_change_reason',
                        f"Balance decreased by {instance._original_amount} due to receipt transfer to {instance.account}")
                    instance._original_account.balance -= instance._original_amount
                    instance._original_account.save(update_fields=['balance'])
                    
                    # Set history reason and update new account
                    instance.account._change_reason = getattr(instance.account, '_change_reason',
                        f"Balance increased by {instance.amount} due to receipt transfer from {instance._original_account}")
                    instance.account.balance += instance.amount
                    instance.account.save(update_fields=['balance'])
                else:
                    # Same account but amount changed
                    delta = instance.amount - instance._original_amount
                    if delta != 0:
                        # Set history reason for receipt
                        instance._change_reason = getattr(instance, '_change_reason',
                            f"Receipt amount changed from {instance._original_amount} to {instance.amount}")
                        
                        # Set history reason for account
                        if delta > 0:
                            change_description = f"Balance increased by {delta} due to receipt amount increase"
                        else:
                            change_description = f"Balance decreased by {abs(delta)} due to receipt amount decrease"
                        
                        instance.account._change_reason = getattr(instance.account, '_change_reason', change_description)
                        
                        # Update account balance
                        instance.account.balance += delta
                        instance.account.save(update_fields=['balance'])

def update_invoice_customer(instance, created):
    """
    Update sales invoice paid amount and customer credit.
    
    Args:
        instance: The Receipt instance that was saved
        created: Boolean indicating if this is a new instance
    """
    if created:
        with transaction.atomic():
            # Set history reason for invoice
            instance.sales_invoice._change_reason = getattr(instance.sales_invoice, '_change_reason',
                f"Paid amount increased by {instance.amount} due to new receipt")
            
            # Update invoice paid amount
            instance.sales_invoice.paid_amount += instance.amount
            instance.sales_invoice.save(update_fields=['paid_amount'])
            
            if instance.sales_invoice.customer:
                # Set history reason for customer
                instance.sales_invoice.customer._change_reason = getattr(instance.sales_invoice.customer, '_change_reason',
                    f"Credit decreased by {instance.amount} due to new receipt for invoice {instance.sales_invoice}")
                
                # Update customer credit
                instance.sales_invoice.customer.credit -= instance.amount
                instance.sales_invoice.customer.save(update_fields=['credit'])
    else:
        if hasattr(instance, '_original_amount') and hasattr(instance, '_original_sales_invoice'):
            with transaction.atomic():
                if instance._original_sales_invoice != instance.sales_invoice:
                    # Invoice changed
                    
                    # Set history reason for original invoice
                    instance._original_sales_invoice._change_reason = getattr(instance._original_sales_invoice, '_change_reason',
                        f"Paid amount decreased by {instance._original_amount} due to receipt transfer to invoice {instance.sales_invoice}")
                    
                    # Update original invoice paid amount
                    instance._original_sales_invoice.paid_amount -= instance._original_amount
                    instance._original_sales_invoice.save(update_fields=['paid_amount'])
                    
                    if instance._original_sales_invoice.customer:
                        # Set history reason for original customer
                        instance._original_sales_invoice.customer._change_reason = getattr(instance._original_sales_invoice.customer, '_change_reason',
                            f"Credit increased by {instance._original_amount} due to receipt transfer to invoice {instance.sales_invoice}")
                        
                        # Update original customer credit
                        instance._original_sales_invoice.customer.credit += instance._original_amount
                        instance._original_sales_invoice.customer.save(update_fields=['credit'])
                    
                    # Set history reason for new invoice
                    instance.sales_invoice._change_reason = getattr(instance.sales_invoice, '_change_reason',
                        f"Paid amount increased by {instance.amount} due to receipt transfer from invoice {instance._original_sales_invoice}")
                    
                    # Update new invoice paid amount
                    instance.sales_invoice.paid_amount += instance.amount
                    instance.sales_invoice.save(update_fields=['paid_amount'])
                    
                    if instance.sales_invoice.customer:
                        # Set history reason for new customer
                        instance.sales_invoice.customer._change_reason = getattr(instance.sales_invoice.customer, '_change_reason',
                            f"Credit decreased by {instance.amount} due to receipt transfer from invoice {instance._original_sales_invoice}")
                        
                        # Update new customer credit
                        instance.sales_invoice.customer.credit -= instance.amount
                        instance.sales_invoice.customer.save(update_fields=['credit'])
                else:
                    # Same invoice but amount changed
                    delta = instance.amount - instance._original_amount
                    if delta != 0:
                        # Determine change description for invoice
                        if delta > 0:
                            invoice_change = f"Paid amount increased by {delta} due to receipt amount increase"
                        else:
                            invoice_change = f"Paid amount decreased by {abs(delta)} due to receipt amount decrease"
                        
                        # Set history reason for invoice
                        instance.sales_invoice._change_reason = getattr(instance.sales_invoice, '_change_reason', invoice_change)
                        
                        # Update invoice paid amount
                        instance.sales_invoice.paid_amount += delta
                        instance.sales_invoice.save(update_fields=['paid_amount'])
                        
                        if instance.sales_invoice.customer:
                            # Determine change description for customer
                            if delta > 0:
                                customer_change = f"Credit decreased by {delta} due to receipt amount increase"
                            else:
                                customer_change = f"Credit increased by {abs(delta)} due to receipt amount decrease"
                            
                            # Set history reason for customer
                            instance.sales_invoice.customer._change_reason = getattr(instance.sales_invoice.customer, '_change_reason', customer_change)
                            
                            # Update customer credit
                            instance.sales_invoice.customer.credit -= delta
                            instance.sales_invoice.customer.save(update_fields=['credit'])

def reverse_receipt_effects(instance):
    """
    Reverse all financial effects of a receipt when it's deleted.
    
    Args:
        instance: The Receipt instance being deleted
    """
    with transaction.atomic():
        # Set history reason for receipt
        instance._change_reason = getattr(instance, '_change_reason',
            f"Receipt of {instance.amount} for invoice {instance.sales_invoice} deleted")
        
        # Set history reason for account
        instance.account._change_reason = getattr(instance.account, '_change_reason',
            f"Balance decreased by {instance.amount} due to receipt deletion")
        
        # Update account balance
        instance.account.balance -= instance.amount
        instance.account.save(update_fields=['balance'])
        
        # Set history reason for invoice
        instance.sales_invoice._change_reason = getattr(instance.sales_invoice, '_change_reason',
            f"Paid amount decreased by {instance.amount} due to receipt deletion")
        
        # Update invoice paid amount
        instance.sales_invoice.paid_amount -= instance.amount
        instance.sales_invoice.save(update_fields=['paid_amount'])
        
        if instance.sales_invoice.customer:
            # Set history reason for customer
            instance.sales_invoice.customer._change_reason = getattr(instance.sales_invoice.customer, '_change_reason',
                f"Credit increased by {instance.amount} due to receipt deletion")
            
            # Update customer credit
            instance.sales_invoice.customer.credit += instance.amount
            instance.sales_invoice.customer.save(update_fields=['credit'])