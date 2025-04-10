from rest_framework import serializers

class TotalBalanceSerializer(serializers.Serializer):
    total_balance = serializers.DecimalField(max_digits=15, decimal_places=2)
