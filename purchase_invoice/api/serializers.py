from rest_framework import serializers
from ..models import PurchaseInvoice

class TotalPayableSerializer(serializers.Serializer):
    total_payable = serializers.DecimalField(max_digits=12, decimal_places=2)

class PurchaseInvoiceSerializer(serializers.ModelSerializer):
    shop_code = serializers.CharField(source='shop.code', read_only=True)
    class Meta:
        model = PurchaseInvoice
        fields = ['id', 'shop_code']