from django.db import models

class Shop(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=255)
    location = models.TextField()
    is_warehouse = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name}({self.code})"

class Supplier(models.Model):
    name = models.CharField(max_length=255)
    contact_info = models.TextField()

    def __str__(self):
        return self.name

class Customer(models.Model):
    name = models.CharField(max_length=255)
    contact_info = models.TextField()
    credit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    credit_limit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    credit_period = models.IntegerField(default=0)  # Days allowed for credit payments

    def __str__(self):
        return f"{self.name} - Credit: {self.credit}/{self.credit_limit} ({self.credit_period} days)"

class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    profit_margin = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)

    def __str__(self):
        return f'{self.name} - Latest selling Price : {self.get_selling_price()}'

    def get_average_cost(self):
        """Calculate the average cost of all purchase invoices."""
        from .purchases import PurchaseInvoiceItem
        purchase_items = PurchaseInvoiceItem.objects.filter(product=self)
        total_cost = sum(item.price * item.quantity for item in purchase_items)
        total_quantity = sum(item.quantity for item in purchase_items)

        return total_cost / total_quantity if total_quantity > 0 else 0

    def get_selling_price(self):
        """Calculate the selling price based on the profit margin."""
        average_cost = self.get_average_cost()
        return average_cost * (1 + self.profit_margin / 100)