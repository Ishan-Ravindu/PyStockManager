from rest_framework import serializers

class TotalReceivablesSerializer(serializers.Serializer):
    total_receivables = serializers.DecimalField(max_digits=15, decimal_places=2)