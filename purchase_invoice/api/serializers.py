from rest_framework import serializers
from django.db.models import Sum, F
from ..models import PurchaseInvoice

class TotalPayableSerializer(serializers.Serializer):
    total_payable = serializers.DecimalField(max_digits=12, decimal_places=2)