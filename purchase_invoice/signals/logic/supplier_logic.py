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
            supplier.payable += Decimal(str(instance.total_amount))
            supplier.save()
            
            logger.info(f"Added {instance.total_amount} to supplier {supplier.pk} payable balance. "
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
    
    # Check if total amount changed
    amount_changed = instance._original_total_amount != instance.total_amount
    
    if not supplier_changed and not amount_changed:
        return  # No relevant changes
    
    with transaction.atomic():
        if supplier_changed:
            # Need to remove amount from old supplier and add to new supplier
            try:
                # Remove from old supplier
                if instance._original_supplier:
                    old_supplier = instance._original_supplier
                    old_supplier.payable -= Decimal(str(instance._original_total_amount))
                    old_supplier.save()
                    
                    logger.info(f"Removed {instance._original_total_amount} from original supplier "
                               f"{old_supplier.pk} payable. New balance: {old_supplier.payable}")
                
                # Add to new supplier
                if instance.supplier:
                    new_supplier = instance.supplier
                    new_supplier.payable += Decimal(str(instance.total_amount))
                    new_supplier.save()
                    
                    logger.info(f"Added {instance.total_amount} to new supplier {new_supplier.pk} payable. "
                               f"New balance: {new_supplier.payable}")
                           
            except Exception as e:
                logger.error(f"Error updating supplier payable on supplier change: {str(e)}")
                raise  # Re-raise to ensure transaction rollback
        
        elif amount_changed:
            # Just need to adjust the existing supplier's balance by the difference
            try:
                supplier = instance.supplier
                
                # Calculate difference and adjust
                amount_difference = Decimal(str(instance.total_amount)) - Decimal(str(instance._original_total_amount))
                supplier.payable += amount_difference
                supplier.save()
                
                logger.info(f"Adjusted supplier {supplier.pk} payable by {amount_difference}. "
                           f"New balance: {supplier.payable}")
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
            supplier.payable -= Decimal(str(instance.total_amount))
            supplier.save()
                
            logger.info(f"Reduced supplier {supplier.pk} payable by {instance.total_amount} due to invoice deletion. "
                       f"New balance: {supplier.payable}")
        except Exception as e:
            logger.error(f"Error updating supplier payable on invoice deletion: {str(e)}")
            raise  # Re-raise to ensure transaction rollback