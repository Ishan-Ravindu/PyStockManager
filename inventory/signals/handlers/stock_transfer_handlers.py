from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.dispatch import receiver
import logging

from inventory.models.stock_transfers import StockTransfer, StockTransferItem
from inventory.signals.logic.stock_transfer_logic import capture_original_item_data, capture_original_transfer_data, process_transfer_item_creation, process_transfer_item_deletion, process_transfer_item_update, process_transfer_shop_changes

# Set up logger
logger = logging.getLogger(__name__)


@receiver(pre_save, sender=StockTransfer)
def store_original_transfer_data(sender, instance, **kwargs):
    """
    Store the original shop values before a StockTransfer is updated.
    
    This allows proper handling of stock quantities when transfer source 
    or destination shops are changed.
    """
    capture_original_transfer_data(instance, logger)


@receiver(post_save, sender=StockTransfer)
def handle_transfer_shop_changes(sender, instance, created, **kwargs):
    """
    When a stock transfer's shops are changed, update all associated items.
    
    This function:
    1. Reverses stock changes from the original shops
    2. Applies stock changes to the new shops
    3. Handles creation of new stock records when needed
    4. Updates average costs appropriately
    """
    if created:
        return  # No need to handle shop changes for new transfers
    
    process_transfer_shop_changes(instance, logger)


@receiver(pre_save, sender=StockTransferItem)
def store_original_item_data(sender, instance, **kwargs):
    """
    Store the original quantity and product before a StockTransferItem is updated.
    
    This allows proper handling of stock quantities when item details change.
    """
    capture_original_item_data(instance, logger)


@receiver(post_save, sender=StockTransferItem)
def update_stock_on_transfer_item_save(sender, instance, created, **kwargs):
    """
    Update stock quantities when a transfer item is created or updated.
    
    For new items:
    - Decrease quantity from source shop
    - Increase quantity in destination shop with appropriate average cost
    
    For updated items:
    - Adjust quantities based on the quantity change
    - Handle product changes
    - Update average costs
    """
    if created:
        process_transfer_item_creation(instance, logger)
    else:
        process_transfer_item_update(instance, logger)


@receiver(post_delete, sender=StockTransferItem)
def update_stock_on_transfer_item_delete(sender, instance, **kwargs):
    """
    When a stock transfer item is deleted, reverse the stock changes.
    
    This function:
    1. Returns quantity to the source shop
    2. Reduces quantity from the destination shop
    3. Maintains average costs appropriately
    """
    process_transfer_item_deletion(instance, logger)