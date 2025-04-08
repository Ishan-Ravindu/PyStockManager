from django.db import models
from utils import phone_regex

class Supplier(models.Model):
    name = models.CharField(max_length=255)
    mobile_number = models.CharField(validators=[phone_regex], max_length=10)
    address = models.TextField(null=True, blank=True)
    email = models.EmailField(max_length=254, null=True, blank=True)
    payable = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return self.name
