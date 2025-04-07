from rest_framework import serializers

from inventory.models.stock import Stock

class StockSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_code = serializers.CharField(source='product.code', read_only=True)
    
    class Meta:
        model = Stock
        fields = ['product_id', 'product_name', 'product_code', 'quantity']