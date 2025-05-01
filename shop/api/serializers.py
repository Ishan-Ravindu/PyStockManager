from rest_framework import serializers

from shop.models import Shop

class ShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ['id', 'name', 'code', 'location', 'is_warehouse']
        read_only_fields = ['id']