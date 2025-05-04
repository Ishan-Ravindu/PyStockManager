from django.forms import ValidationError
from django.utils import timezone

from inventory.models.stock import Stock

class CustomerValidator:
    @staticmethod
    def validate_blacklist(customer):
        if customer and customer.black_list:
            raise ValidationError("Cannot create an invoice for a blacklisted customer.")

    @staticmethod
    def validate_due_date(due_date, customer, today=None):
        if not due_date or not customer:
            return
        today = today or timezone.now().date()
        if due_date < today:
            raise ValidationError("Due date cannot be earlier than today.")
        max_credit_date = today + timezone.timedelta(days=customer.credit_period)
        if due_date > max_credit_date:
            raise ValidationError(
                f"Due date cannot exceed customer credit period ({customer.credit_period} days)."
            )

class InventoryValidator:
    @staticmethod
    def validate_stock_quantity(product, quantity, shop):
        if not all([product, quantity, shop]):
            return        
        try:
            stock = product.stock_set.get(shop=shop)            
            if quantity > stock.quantity:
                raise ValidationError(
                    f"Quantity {quantity} exceeds available stock {stock.quantity} for {product.name} in {shop.name}."
                )
        except product.stock_set.model.DoesNotExist:
            raise ValidationError(f"No stock available for {product.name} in {shop.name}.")
        except Exception as e:
            raise ValidationError(f"{str(e)}")
        
    @staticmethod
    def validate_price_not_below_selling_price(self, product, price, shop):
        """
        Validate that the invoice price isn't below the product's selling price.
        This would be implemented in your InventoryValidator class.
        """
        try:
            stock = Stock.objects.get(shop=shop, product=product)
            if price < stock.selling_price:
                raise ValidationError(
                    f"Price ({price}) cannot be lower than the product's selling price ({stock.selling_price})"
                )
        except Stock.DoesNotExist:
            pass
            # raise ValidationError(f"No stock available for {product.name} in {shop.name}.")

class InvoiceValidator:
    @staticmethod
    def validate_has_items(items_count):
        if items_count == 0:
            raise ValidationError("Invoice must have at least one valid item.")

    @staticmethod
    def validate_can_edit(invoice):
        if invoice and invoice.receipts.exists():
            receipt_list = ", ".join([str(r.id) for r in invoice.receipts.all()[:5]])
            if invoice.receipts.count() > 5:
                receipt_list += f" (and {invoice.receipts.count() - 5} more)"
            raise ValidationError(
                f"Cannot edit Invoice #{invoice.id} ({invoice.shop.code}) because it has linked receipts: {receipt_list}"
            )