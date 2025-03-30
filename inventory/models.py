from django.db import models
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver

class Shop(models.Model):
    name = models.CharField(max_length=255)
    location = models.TextField()
    is_warehouse = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class Supplier(models.Model):
    name = models.CharField(max_length=255)
    contact_info = models.TextField()

    def __str__(self):
        return self.name

class Customer(models.Model):
    name = models.CharField(max_length=255)
    contact_info = models.TextField()
    credit_limit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    credit_period = models.IntegerField(default=0)  # Days allowed for credit payments

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    profit_margin = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)

    def __str__(self):
        return self.name

    def get_average_cost(self):
        """Calculate the average cost of all purchase invoices."""
        purchase_items = PurchaseInvoiceItem.objects.filter(product=self)
        total_cost = sum(item.price * item.quantity for item in purchase_items)
        total_quantity = sum(item.quantity for item in purchase_items)

        return total_cost / total_quantity if total_quantity > 0 else 0

    def get_selling_price(self):
        """Calculate the selling price based on the profit margin."""
        average_cost = self.get_average_cost()
        return average_cost * (1 + self.profit_margin / 100)

class Stock(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.shop.name} - {self.product.name} ({self.quantity})"

    def update_stock(self, quantity_change):
        """Update stock with a controlled function (prevents direct admin changes)."""
        self.quantity += quantity_change
        self.save()

class PurchaseInvoice(models.Model):
    supplier = models.ForeignKey('Supplier', on_delete=models.SET_NULL, null=True)
    shop = models.ForeignKey('Shop', on_delete=models.CASCADE)  # Warehouse
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Purchase {self.id} from {self.supplier.name}"

    def update_total_amount(self):
        """Calculate and update total amount from invoice items."""
        total = sum(item.price * item.quantity for item in self.purchaseinvoiceitem_set.all())
        self.total_amount = total
        self.save()

class PurchaseInvoiceItem(models.Model):
    purchase_invoice = models.ForeignKey(PurchaseInvoice, on_delete=models.CASCADE)
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} - {self.quantity} pcs"

@receiver(post_save, sender=PurchaseInvoiceItem)
def update_stock_and_price_after_purchase(sender, instance, **kwargs):
    """Update stock and recalculate average cost after a purchase."""
    stock, created = Stock.objects.get_or_create(shop=instance.purchase_invoice.shop, product=instance.product)
    stock.update_stock(instance.quantity)

@receiver(post_save, sender=PurchaseInvoiceItem)
@receiver(post_delete, sender=PurchaseInvoiceItem)
def recalculate_total_amount(sender, instance, **kwargs):
    """Update total amount of purchase invoice when items change."""
    instance.purchase_invoice.update_total_amount()

class StockTransfer(models.Model):
    from_shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='outgoing_transfers')
    to_shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='incoming_transfers')
    created_at = models.DateTimeField(auto_now_add=True)

class StockTransferItem(models.Model):
    stock_transfer = models.ForeignKey(StockTransfer, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()

@receiver(post_save, sender=StockTransferItem)
def update_stock_after_transfer(sender, instance, **kwargs):
    from_stock = Stock.objects.get(shop=instance.stock_transfer.from_shop, product=instance.product)
    to_stock, created = Stock.objects.get_or_create(shop=instance.stock_transfer.to_shop, product=instance.product)
    
    from_stock.update_stock(-instance.quantity)
    to_stock.update_stock(instance.quantity)

class SalesInvoice(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True)
    shop = models.ForeignKey('Shop', on_delete=models.CASCADE)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Sales {self.id} to {self.customer.name}"

    def update_total_amount(self):
        """Calculate and update total amount from sales invoice items."""
        total = sum(item.price * item.quantity for item in self.items.all())
        self.total_amount = total
        self.save()

class SalesInvoiceItem(models.Model):
    sales_invoice = models.ForeignKey(SalesInvoice, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)  # Auto-populated

    def __str__(self):
        return f"{self.product.name} - {self.quantity} pcs"

@receiver(post_save, sender=SalesInvoiceItem)
def update_stock_after_sale(sender, instance, **kwargs):
    stock = Stock.objects.get(shop=instance.sales_invoice.shop, product=instance.product)
    stock.update_stock(-instance.quantity)

@receiver(post_save, sender=SalesInvoiceItem)
@receiver(post_delete, sender=SalesInvoiceItem)
def recalculate_sales_total_amount(sender, instance, **kwargs):
    """Update total amount of sales invoice when items change."""
    if instance.sales_invoice:
        instance.sales_invoice.update_total_amount()

@receiver(pre_save, sender=SalesInvoiceItem)
def populate_sales_price(sender, instance, **kwargs):
    """Auto-populate price from product's selling price if not set."""
    if instance.price is None:
        instance.price = instance.product.get_selling_price()
