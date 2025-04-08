from django.db import models

class Shop(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=255)
    location = models.TextField()
    is_warehouse = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.code}"