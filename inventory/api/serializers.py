from rest_framework import serializers

from inventory.models.stock import Stock

class StockSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_code = serializers.CharField(source='product.code', read_only=True)
    
    class Meta:
        model = Stock
        fields = ['product_id', 'product_name', 'product_code', 'quantity']

class InventoryValueSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    inventory_value = serializers.SerializerMethodField()
    
    class Meta:
        model = Stock
        fields = ['product_id', 'product_name', 'quantity', 
                 'average_cost', 'inventory_value']
    
    def get_inventory_value(self, obj):
        """Calculate inventory value as average_cost * quantity"""
        return obj.average_cost * obj.quantity