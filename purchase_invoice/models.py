from django.db import models

class PurchaseInvoice(models.Model):
    supplier = models.ForeignKey('supplier.supplier', on_delete=models.SET_NULL, null=True)
    shop = models.ForeignKey('shop.Shop', on_delete=models.CASCADE)  # Warehouse
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, editable=False)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, editable=False)
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
    product = models.ForeignKey('product.Product', on_delete=models.CASCADE)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} - {self.quantity} pcs"