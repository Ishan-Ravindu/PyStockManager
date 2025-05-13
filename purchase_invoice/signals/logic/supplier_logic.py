from decimal import Decimal
from django.db import transaction
import logging

def update_supplier_payable_on_create(instance, logger):
    """
    Update supplier payable when a new purchase invoice is created.
    
    Args:
        instance: The new PurchaseInvoice instance
        logger: Logger instance for recording operations
    """
    if not hasattr(instance, 'supplier') or instance.supplier is None:
        logger.warning(f"Invoice {instance.pk} has no supplier, skipping payable update")
        return

    with transaction.atomic():
        try:
            supplier = instance.supplier
            # Convert to Decimal to ensure compatible types
            invoice_amount = Decimal(str(instance.total_amount))
            
            # For a new invoice, add the total amount to supplier payable
            supplier.payable = supplier.payable + invoice_amount
            supplier.save(update_fields=['payable'])  # Only update the payable field
            
            logger.info(f"Added {invoice_amount} to supplier {supplier.pk} payable balance for new invoice. "
                       f"New balance: {supplier.payable}")
        except Exception as e:
            logger.error(f"Error updating supplier payable on new invoice: {str(e)}")
            raise  # Re-raise to ensure transaction rollback


def update_supplier_payable_on_update(instance, logger):
    """
    Update supplier payable when a purchase invoice is updated.
    
    Args:
        instance: The updated PurchaseInvoice instance
        logger: Logger instance for recording operations
    """
    if not hasattr(instance, 'supplier') or instance.supplier is None:
        logger.warning(f"Invoice {instance.pk} has no supplier, skipping payable update")
        return
        
    # Check if we have the original data
    if not hasattr(instance, '_original_supplier') or not hasattr(instance, '_original_total_amount'):
        logger.warning(f"Missing original data for invoice {instance.pk}, skipping payable update")
        return
        
    # Check if supplier changed
    supplier_changed = instance._original_supplier != instance.supplier
    
    # Check if total amount changed - convert to decimals for safe comparison
    original_amount = Decimal(str(instance._original_total_amount))
    current_amount = Decimal(str(instance.total_amount))
    amount_changed = original_amount != current_amount
    amount_difference = current_amount - original_amount
    
    if not supplier_changed and not amount_changed:
        logger.debug(f"No relevant changes to invoice {instance.pk}, skipping payable update")
        return  # No relevant changes
    
    # Log the change details
    logger.info(f"Invoice {instance.pk} update details: supplier_changed={supplier_changed}, "
               f"original_amount={original_amount}, current_amount={current_amount}, "
               f"difference={amount_difference}")
    
    with transaction.atomic():
        if supplier_changed:
            # Need to remove amount from old supplier and add to new supplier
            try:
                # Remove from old supplier
                if instance._original_supplier:
                    old_supplier = instance._original_supplier
                    old_supplier.payable = old_supplier.payable - original_amount
                    old_supplier.save(update_fields=['payable'])
                    
                    logger.info(f"Removed {original_amount} from original supplier "
                               f"{old_supplier.pk} payable. New balance: {old_supplier.payable}")
                
                # Add to new supplier
                if instance.supplier:
                    new_supplier = instance.supplier
                    new_supplier.payable = new_supplier.payable + current_amount
                    new_supplier.save(update_fields=['payable'])
                    
                    logger.info(f"Added {current_amount} to new supplier {new_supplier.pk} payable. "
                               f"New balance: {new_supplier.payable}")
                           
            except Exception as e:
                logger.error(f"Error updating supplier payable on supplier change: {str(e)}")
                raise  # Re-raise to ensure transaction rollback
        
        elif amount_changed:
            # Just need to adjust the existing supplier's balance by the difference
            try:
                supplier = instance.supplier
                
                # Add the difference to the supplier's payable
                # If the invoice total increased, this will be positive
                # If the invoice total decreased, this will be negative
                supplier.payable = supplier.payable + amount_difference
                supplier.save(update_fields=['payable'])
                
                logger.info(f"Adjusted supplier {supplier.pk} payable by {amount_difference}. "
                           f"Original amount: {original_amount}, New amount: {current_amount}, "
                           f"New balance: {supplier.payable}")
                
                # Mark this instance as having its supplier payable updated
                # This will prevent the item-level signal from updating it again
                instance._supplier_payable_updated = True
                
            except Exception as e:
                logger.error(f"Error updating supplier payable on amount change: {str(e)}")
                raise  # Re-raise to ensure transaction rollback


def update_supplier_payable_on_delete(instance, logger):
    """
    Update supplier payable when a purchase invoice is deleted.
    
    Args:
        instance: The PurchaseInvoice instance being deleted
        logger: Logger instance for recording operations
    """
    if not hasattr(instance, 'supplier') or instance.supplier is None:
        logger.warning(f"Deleted invoice had no supplier, skipping payable update")
        return
        
    supplier = instance.supplier
    
    with transaction.atomic():
        try:
            # When deleting an invoice, subtract its total from the supplier's payable
            invoice_amount = Decimal(str(instance.total_amount))
            supplier.payable = supplier.payable - invoice_amount
            supplier.save(update_fields=['payable'])
                
            logger.info(f"Reduced supplier {supplier.pk} payable by {invoice_amount} due to invoice deletion. "
                       f"New balance: {supplier.payable}")
        except Exception as e:
            logger.error(f"Error updating supplier payable on invoice deletion: {str(e)}")
            raise  # Re-raise to ensure transaction rollback


def handle_invoice_save(instance, created, logger):
    """
    Handle the business logic for when an invoice is saved.
    This centralizes the logic that would otherwise be in the signal handler.
    
    Args:
        instance: The PurchaseInvoice instance
        created: Boolean indicating if this is a new instance
        logger: Logger instance for recording operations
    """
    if created:
        # For new invoices, add the full amount to supplier payable
        update_supplier_payable_on_create(instance, logger)
    else:
        # For updated invoices, only add/subtract the difference
        update_supplier_payable_on_update(instance, logger)


def handle_invoice_item_save(instance, created, logger):
    """
    Handle the business logic for when an invoice item is saved.
    This centralizes the logic that would otherwise be in the signal handler.
    
    Args:
        instance: The PurchaseInvoiceItem instance
        created: Boolean indicating if this is a new instance
        logger: Logger instance for recording operations
    """
    invoice = instance.purchase_invoice
    
    # Completely disable this function as we're letting the invoice post_save handle all updates
    # This is the key change - we're not doing any supplier payable updates at the item level anymore
    # Instead, we'll rely on the invoice's total amount being updated and then the invoice's post_save signal
    # will handle updating the supplier payable
    
    with transaction.atomic():
        # Update the invoice total - this will trigger the invoice's post_save signal
        old_total = invoice.total_amount
        invoice.update_total_amount()
        new_total = invoice.total_amount
        
        # Only save the invoice if the total actually changed
        if old_total != new_total:
            logger.debug(f"Updating invoice {invoice.pk} total from {old_total} to {new_total}")
            invoice.save(update_fields=['total_amount'])
            
            # Note: We do NOT update the supplier payable here.
            # The invoice's post_save signal will handle that.


def handle_invoice_item_delete(instance, logger):
    """
    Handle the business logic for when an invoice item is deleted.
    This centralizes the logic that would otherwise be in the signal handler.
    
    Args:
        instance: The PurchaseInvoiceItem instance being deleted
        logger: Logger instance for recording operations
    """
    try:
        invoice = instance.purchase_invoice
        if not invoice or not invoice.supplier:
            return
        
        with transaction.atomic():
            # Update the invoice total - this will trigger the invoice's post_save signal
            old_total = invoice.total_amount
            invoice.update_total_amount()
            new_total = invoice.total_amount
            
            # Only save the invoice if the total actually changed
            if old_total != new_total:
                logger.debug(f"Updating invoice {invoice.pk} total from {old_total} to {new_total} after item deletion")
                invoice.save(update_fields=['total_amount'])
                
                # Note: We do NOT update the supplier payable here.
                # The invoice's post_save signal will handle that.
                
    except Exception as e:
        logger.error(f"Error updating invoice total after item deletion: {str(e)}")
        # Let the exception propagate to rollback the transaction