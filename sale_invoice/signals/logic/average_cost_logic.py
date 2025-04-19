from inventory.models.stock import Stock

def update_sales_invoice_item_average_cost(item):
    """
    Update the average_cost of a SalesInvoiceItem with the 
    product's average cost from the corresponding Stock entry.
    
    Args:
        item: The SalesInvoiceItem instance to update
    
    Returns:
        bool: True if the average_cost was updated, False otherwise
    """
    if item.average_cost is None or getattr(item, '_update_average_cost', False):
        try:
            shop = item.sales_invoice.shop
            stock = Stock.objects.get(
                shop=shop,
                product=item.product
            )
            item.average_cost = stock.average_cost
            if hasattr(item, '_update_average_cost'):
                delattr(item, '_update_average_cost')
                
            return True
            
        except Stock.DoesNotExist:
            return False
    
    return False