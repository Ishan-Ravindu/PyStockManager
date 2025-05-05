from django.db import transaction
from decimal import Decimal

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
            
            # Convert float to decimal or decimal to float based on target type
            amount = instance.amount
            if isinstance(instance.sales_invoice.paid_amount, float) and isinstance(amount, Decimal):
                # If paid_amount is float, convert amount to float
                amount = float(amount)
            elif isinstance(instance.sales_invoice.paid_amount, Decimal) and not isinstance(amount, Decimal):
                # If paid_amount is Decimal, convert amount to Decimal
                amount = Decimal(str(amount))
            
            # Update invoice paid amount
            instance.sales_invoice.paid_amount += amount
            instance.sales_invoice.save(update_fields=['paid_amount'])
            
            if instance.sales_invoice.customer:
                # Set history reason for customer
                instance.sales_invoice.customer._change_reason = getattr(instance.sales_invoice.customer, '_change_reason',
                    f"Credit decreased by {amount} due to new receipt for invoice {instance.sales_invoice}")
                
                # Ensure type compatibility for customer credit
                customer_amount = amount
                if isinstance(instance.sales_invoice.customer.credit, Decimal) and not isinstance(customer_amount, Decimal):
                    customer_amount = Decimal(str(customer_amount))
                elif isinstance(instance.sales_invoice.customer.credit, float) and isinstance(customer_amount, Decimal):
                    customer_amount = float(customer_amount)
                
                # Update customer credit - FIXED: This should be SUBTRACTED from credit
                instance.sales_invoice.customer.credit -= customer_amount
                instance.sales_invoice.customer.save(update_fields=['credit'])
    else:
        if hasattr(instance, '_original_amount') and hasattr(instance, '_original_sales_invoice'):
            with transaction.atomic():
                if instance._original_sales_invoice != instance.sales_invoice:
                    # Invoice changed
                    
                    # Convert amounts based on target type
                    original_amount = instance._original_amount
                    if isinstance(instance._original_sales_invoice.paid_amount, float) and isinstance(original_amount, Decimal):
                        # If paid_amount is float, convert amount to float
                        original_amount = float(original_amount)
                    elif isinstance(instance._original_sales_invoice.paid_amount, Decimal) and not isinstance(original_amount, Decimal):
                        # If paid_amount is Decimal, convert amount to Decimal
                        original_amount = Decimal(str(original_amount))
                    
                    current_amount = instance.amount
                    if isinstance(instance.sales_invoice.paid_amount, float) and isinstance(current_amount, Decimal):
                        # If paid_amount is float, convert amount to float
                        current_amount = float(current_amount)
                    elif isinstance(instance.sales_invoice.paid_amount, Decimal) and not isinstance(current_amount, Decimal):
                        # If paid_amount is Decimal, convert amount to Decimal
                        current_amount = Decimal(str(current_amount))
                    
                    # Set history reason for original invoice
                    instance._original_sales_invoice._change_reason = getattr(instance._original_sales_invoice, '_change_reason',
                        f"Paid amount decreased by {original_amount} due to receipt transfer to invoice {instance.sales_invoice}")
                    
                    # Update original invoice paid amount
                    instance._original_sales_invoice.paid_amount -= original_amount
                    instance._original_sales_invoice.save(update_fields=['paid_amount'])
                    
                    if instance._original_sales_invoice.customer:
                        # Set history reason for original customer
                        instance._original_sales_invoice.customer._change_reason = getattr(instance._original_sales_invoice.customer, '_change_reason',
                            f"Credit increased by {original_amount} due to receipt transfer to invoice {instance.sales_invoice}")
                        
                        # Update original customer credit - FIXED: When paid amount is removed, ADD to credit
                        customer_original_amount = original_amount
                        if isinstance(instance._original_sales_invoice.customer.credit, Decimal) and not isinstance(customer_original_amount, Decimal):
                            customer_original_amount = Decimal(str(customer_original_amount))
                        elif isinstance(instance._original_sales_invoice.customer.credit, float) and isinstance(customer_original_amount, Decimal):
                            customer_original_amount = float(customer_original_amount)
                            
                        instance._original_sales_invoice.customer.credit += customer_original_amount
                        instance._original_sales_invoice.customer.save(update_fields=['credit'])
                    
                    # Set history reason for new invoice
                    instance.sales_invoice._change_reason = getattr(instance.sales_invoice, '_change_reason',
                        f"Paid amount increased by {current_amount} due to receipt transfer from invoice {instance._original_sales_invoice}")
                    
                    # Update new invoice paid amount
                    instance.sales_invoice.paid_amount += current_amount
                    instance.sales_invoice.save(update_fields=['paid_amount'])
                    
                    if instance.sales_invoice.customer:
                        # Set history reason for new customer
                        instance.sales_invoice.customer._change_reason = getattr(instance.sales_invoice.customer, '_change_reason',
                            f"Credit decreased by {current_amount} due to receipt transfer from invoice {instance._original_sales_invoice}")
                        
                        # Update new customer credit - FIXED: When paid amount is added, SUBTRACT from credit
                        customer_current_amount = current_amount
                        if isinstance(instance.sales_invoice.customer.credit, Decimal) and not isinstance(customer_current_amount, Decimal):
                            customer_current_amount = Decimal(str(customer_current_amount))
                        elif isinstance(instance.sales_invoice.customer.credit, float) and isinstance(customer_current_amount, Decimal):
                            customer_current_amount = float(customer_current_amount)
                            
                        instance.sales_invoice.customer.credit -= customer_current_amount
                        instance.sales_invoice.customer.save(update_fields=['credit'])
                else:
                    # Same invoice but amount changed
                    delta = instance.amount - instance._original_amount
                    
                    # Convert delta to Decimal if needed
                    if delta != 0:
                        if not isinstance(delta, Decimal) and hasattr(instance.sales_invoice, 'paid_amount'):
                            if isinstance(instance.sales_invoice.paid_amount, Decimal):
                                delta = Decimal(str(delta))
                        
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
                            
                            # Update customer credit - FIXED: When paid amount increases, credit should DECREASE
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
        
        # Convert amount based on target type
        amount = instance.amount
        if isinstance(instance.sales_invoice.paid_amount, float) and isinstance(amount, Decimal):
            # If paid_amount is float, convert amount to float
            amount = float(amount)
        elif isinstance(instance.sales_invoice.paid_amount, Decimal) and not isinstance(amount, Decimal):
            # If paid_amount is Decimal, convert amount to Decimal
            amount = Decimal(str(amount))
        
        # Set history reason for invoice
        instance.sales_invoice._change_reason = getattr(instance.sales_invoice, '_change_reason',
            f"Paid amount decreased by {amount} due to receipt deletion")
        
        # Update invoice paid amount
        instance.sales_invoice.paid_amount -= amount
        instance.sales_invoice.save(update_fields=['paid_amount'])
        
        if instance.sales_invoice.customer:
            # Set history reason for customer
            instance.sales_invoice.customer._change_reason = getattr(instance.sales_invoice.customer, '_change_reason',
                f"Credit increased by {amount} due to receipt deletion")
            
            # Ensure type compatibility for customer credit
            customer_amount = amount
            if isinstance(instance.sales_invoice.customer.credit, Decimal) and not isinstance(customer_amount, Decimal):
                customer_amount = Decimal(str(customer_amount))
            elif isinstance(instance.sales_invoice.customer.credit, float) and isinstance(customer_amount, Decimal):
                customer_amount = float(customer_amount)
            
            # Update customer credit - FIXED: When receipt is deleted, ADD to credit
            instance.sales_invoice.customer.credit += customer_amount
            instance.sales_invoice.customer.save(update_fields=['credit'])